import json
import logging
import time
import re
from openai import OpenAI
from backend.scripts.scanner import resolve_model_and_url

def analyser_doublons_identiques(lot_amendements: list[dict], model_name: str = "mac_mistral"):
    """
    Étape 2 du pipeline : Traite un lot d'amendements (déjà trié par sorting_engine.py) 
    pour détecter les "Doublons", "Identiques" ou incompatibilités via le LLM.
    
    Application de la doctrine :
    - Identiques : Corps (texte modificatif) similaire, Auteurs DIFFÉRENTS (Recevable, mais regroupé).
    - Doublons : Corps (texte modificatif) similaire, MÊME Auteur (Irrécevable).
    - Chutes (Incompatibilité de fond) : Signalées par l'IA si adoption impossible des deux.
    """
    target_url, model_id = resolve_model_and_url(model_name)
    client = OpenAI(base_url=target_url, api_key="lm-studio", timeout=300.0)
    
    resultats = []
    
    system_prompt = (
        "Tu es un expert en procédure législative de l'Assemblée nationale. "
        "Ton unique mission est d'analyser le corps de deux amendements pour statuer sur leur relation sémantique. "
        "CONSIGNES STRICTES :\n"
        "1. IGNORE le 'chapeau' de l'amendement (ex: 'À l'article 3, alinéa 4...'). Ne compare que le sens du texte ajouté/modifié.\n"
        "2. Compare les auteurs. Si le sens est similaire ET l'auteur est identique = 'Doublon'.\n"
        "3. Si le sens est similaire MAIS les auteurs sont différents = 'Identique'.\n"
        "4. Si le sens est fondamentalement opposé et incompatible = 'Incompatible' (Chute de fond).\n"
        "5. Sinon, c'est 'Nouveau'.\n"
        "FORMAT DE RÉPONSE : Tu dois répondre UNIQUEMENT par un JSON valide avec les clés 'statut' (Doublon, Identique, Incompatible, Nouveau) et 'justification' (1 phrase maximum expliquant pourquoi)."
    )
    
    # Afin de ne pas surcharger le modèle local, nous comparons séquentiellement
    # l'amendement actuel à l'amendement "référence" de son groupe de tri.
    amendement_precedent = None
    
    for i, amendement in enumerate(lot_amendements):
        amend_id = amendement.get("numero", f"ID_{i}")
        auteur = amendement.get("auteur", "Inconnu")
        texte = amendement.get("texte", "")
        
        if amendement_precedent is None:
            # Le tout premier amendement d'un lot est toujours "Nouveau"
            resultats.append({
                "id": amend_id,
                "statut": "Nouveau",
                "justification": "Premier amendement du lot (Référence).",
                "alerte_couleur": "vert"
            })
            amendement_precedent = amendement
            continue
            
        # Construction du prompt comparatif
        user_prompt = (
            f"--- AMENDEMENT DE RÉFÉRENCE ---\n"
            f"Auteur : {amendement_precedent.get('auteur', '')}\n"
            f"Texte : {amendement_precedent.get('texte', '')}\n\n"
            f"--- AMENDEMENT À ANALYSER ---\n"
            f"Auteur : {auteur}\n"
            f"Texte : {texte}\n"
        )
        
        full_prompt = f"[INSTRUCTION SYSTÈME] {system_prompt}\n\n[REQUÊTE]\n{user_prompt}"
        
        try:
            logging.info(f"🧠 Envoi au LLM ({model_id}) de l'amendement {amend_id} pour détection de doublon...")
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": full_prompt}],
                temperature=0.1,  # Très bas pour maximiser la logique stricte
                max_tokens=200,
            )
            
            contenu = response.choices[0].message.content.strip()
            
            # Extraction du JSON
            match = re.search(r"```(?:json)?(.*?)```", contenu, re.DOTALL | re.IGNORECASE)
            if match:
                contenu = match.group(1).strip()
                
            data_json = json.loads(contenu)
            
            statut = data_json.get("statut", "Nouveau")
            alerte = "vert"
            if statut == "Doublon":
                alerte = "rouge"
            elif statut in ["Identique", "Incompatible"]:
                alerte = "orange"
                
            resultats.append({
                "id": amend_id,
                "statut": statut,
                "justification": data_json.get("justification", "Analyse réussie"),
                "alerte_couleur": alerte
            })
            
            # Si l'amendement est "Nouveau" (sens différent), il devient la nouvelle référence pour les suivants.
            if statut == "Nouveau":
                amendement_precedent = amendement
                
        except Exception as e:
            logging.error(f"❌ Erreur lors de l'analyse LLM pour {amend_id} : {e}")
            resultats.append({
                "id": amend_id,
                "statut": "Erreur",
                "justification": f"Échec de traitement NLP : {e}",
                "alerte_couleur": "rouge"
            })
            
        # ⚠️ CRUCIAL : Gestion du délai (Sleep) pour préserver les ressources GPU/CPU du Mac Local.
        # Permet de séquencer les requêtes sans timeout.
        time.sleep(1.5)
        
    return resultats
