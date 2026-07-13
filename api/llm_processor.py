import re
import os
from dotenv import load_dotenv

load_dotenv()


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
    elif "auteur" in amendement or "auteurs" in amendement:
        auteur = amendement.get("auteur", ", ".join(amendement.get("auteurs", [])))
        
    # Extraction Dispositif & Exposé
    dispositif = amendement.get("dispositif", amendement.get("texte", ""))
    expose = amendement.get("expose_sommaire", amendement.get("motif", ""))
    
    if "corps" in amendement and "contenuAuteur" in amendement["corps"]:
        contenu = amendement["corps"]["contenuAuteur"]
        dispositif = contenu.get("dispositif", dispositif)
        expose = contenu.get("exposeSommaire", expose)
        
    # Nettoyage des balises HTML parasites
    dispositif = re.sub(r'<[^>]+>', '', dispositif)
    expose = re.sub(r'<[^>]+>', '', expose)
    
    return {
        "auteur": auteur[:100], 
        "texte": f"Dispositif: {dispositif[:1000]}\nExposé: {expose[:500]}"
    }

# NOTE: La fonction analyser_doublons_identiques a été fusionnée dans 
# api/index.py pour permettre l'interruption asynchrone (Bouton Stop).
