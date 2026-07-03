import json
import time
import re
from openai import OpenAI
from backend.scripts.scanner import resolve_model_and_url

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
    
    amendement_precedent = None
    
    for i, amendement in enumerate(lot_amendements):
        amend_id = amendement.get("numero", f"ID_{i}")
        
        if amendement_precedent is None:
            resultats.append({
                "id": amend_id, "statut": "Nouveau", 
                "justification": "Premier du lot (Référence).", "alerte_couleur": "vert"
            })
            amendement_precedent = amendement
            continue
            
        user_prompt = (
            f"REF - Auteur: {amendement_precedent.get('auteur')}\nTexte: {amendement_precedent.get('texte')}\n"
            f"TEST - Auteur: {amendement.get('auteur')}\nTexte: {amendement.get('texte')}"
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
            data_json = json.loads(contenu)
            
            statut = data_json.get("statut", "Nouveau")
            couleur = "rouge" if statut == "Doublon" else "orange" if statut in ["Identique", "Incompatible"] else "vert"
                
            resultats.append({
                "id": amend_id, "statut": statut,
                "justification": data_json.get("justification", ""),
                "alerte_couleur": couleur
            })
            
            if statut == "Nouveau":
                amendement_precedent = amendement
                
        except Exception as e:
            resultats.append({
                "id": amend_id, "statut": "Erreur",
                "justification": str(e), "alerte_couleur": "rouge"
            })
            
        if i < len(lot_amendements) - 1:
            time.sleep(1.5)
        
    return resultats
