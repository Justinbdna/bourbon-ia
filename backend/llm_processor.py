import json
import time
import re
from openai import OpenAI
from backend.scripts.scanner import resolve_model_and_url

def extraire_texte_brut(amendement: dict) -> dict:
    """
    Extrait les données vitales d'un JSON brut de l'Assemblée nationale
    pour éviter la surcharge de contexte du LLM.
    """
    # Extraction Auteur
    auteur = "Inconnu"
    if "signataires" in amendement:
        auteurs = amendement["signataires"].get("auteur", {})
        if isinstance(auteurs, dict):
            auteur = auteurs.get("acteurRef", "Inconnu")
        elif isinstance(auteurs, list) and len(auteurs) > 0:
            auteur = auteurs[0].get("acteurRef", "Inconnu")
    elif "auteur" in amendement:
        auteur = amendement["auteur"]
        
    # Extraction Dispositif & Exposé
    dispositif = amendement.get("texte", "")
    expose = amendement.get("motif", "")
    
    if "corps" in amendement and "contenuAuteur" in amendement["corps"]:
        contenu = amendement["corps"]["contenuAuteur"]
        dispositif = contenu.get("dispositif", dispositif)
        expose = contenu.get("exposeSommaire", expose)
        
    # Nettoyage des balises HTML parasites potentielles
    dispositif = re.sub(r'<[^>]+>', '', dispositif)
    expose = re.sub(r'<[^>]+>', '', expose)
    
    return {
        "auteur": auteur[:100],  # Sécurité sur la longueur
        "texte": f"Dispositif: {dispositif[:1000]}\nExposé: {expose[:500]}"
    }

def analyser_doublons_identiques(lot_amendements: list[dict], model_name: str = "mac_mistral") -> list[dict]:
    """
    Étape 2 du pipeline : Détecte les Doublons, Identiques ou Incompatibles.
    """
    target_url, model_id = resolve_model_and_url(model_name)
    client = OpenAI(base_url=target_url, api_key="lm-studio", timeout=300.0)
    
    resultats = []
    
    system_prompt = (
        "Tu es un assistant juridique. Compare ces amendements en ignorant le 'chapeau'. "
        "Réponds UNIQUEMENT en JSON avec les clés : id, statut (Doublon, Identique, Nouveau, Incompatible), justification."
    )
    
    # Réinitialisé à chaque lot pour éviter l'accumulation
    amendement_precedent = None
    
    for i, amendement in enumerate(lot_amendements):
        amend_id = amendement.get("numero", f"ID_{i}")
        donnees_propres = extraire_texte_brut(amendement)
        
        if amendement_precedent is None:
            resultats.append({
                "id": amend_id, "statut": "Nouveau", 
                "justification": "Premier du lot (Référence).", "alerte_couleur": "vert"
            })
            amendement_precedent = donnees_propres
            continue
            
        user_prompt = (
            f"REF - Auteur: {amendement_precedent['auteur']}\nTexte: {amendement_precedent['texte']}\n"
            f"TEST - Auteur: {donnees_propres['auteur']}\nTexte: {donnees_propres['texte']}"
        )
        
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.1,
                max_tokens=200,
            )
            contenu = response.choices[0].message.content.strip()
            match = re.search(r"```(?:json)?(.*?)```", contenu, re.DOTALL | re.IGNORECASE)
            if match:
                contenu = match.group(1).strip()
                
            # Extraction stricte de ce qui ressemble à un objet ou tableau JSON
            json_match = re.search(r'\[.*\]|\{.*\}', contenu, re.DOTALL)
            if json_match:
                contenu = json_match.group(0)
                
            try:
                data_json = json.loads(contenu)
            except json.JSONDecodeError:
                data_json = {"statut": "Erreur", "justification": "Erreur de formatage du modèle."}
            
            statut = data_json.get("statut", "Nouveau")
            couleur = "rouge" if statut == "Doublon" else "orange" if statut in ["Identique", "Incompatible"] else "vert"
                
            resultats.append({
                "id": amend_id, "statut": statut,
                "justification": data_json.get("justification", ""),
                "alerte_couleur": couleur
            })
            
            if statut == "Nouveau":
                amendement_precedent = donnees_propres
                
        except Exception as e:
            resultats.append({
                "id": amend_id, "statut": "Erreur",
                "justification": str(e), "alerte_couleur": "rouge"
            })
            
        if i < len(lot_amendements) - 1:
            time.sleep(1.5)
        
    return resultats
