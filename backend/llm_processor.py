import re
import os
from dotenv import load_dotenv

load_dotenv()

# --- Configuration LM Studio ---
PC_URL = os.environ.get("LLM_API_URL", "http://100.78.180.81:1234/v1")
MAC_URL = "http://127.0.0.1:1234/v1"

MODEL_MAP = {
    "mac_mistral": "mistralai/mistral-7b-instruct-v0.3",
    "mac_llama": "lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF",
    "mac_qwen": "qwen/qwen3.5-9b",
    "mac_gemma": "google/gemma-4-e2b",
    "pc_mistral_7b": "mistralai/mistral-7b-instruct-v0.3",
    "pc_mistral_14b": "mistralai/ministral-3-14b-reasoning",
    "pc_gemma_12b": "google/gemma-4-12b",
    "pc_qwen_35b": "qwen/qwen3.6-35b-a3b",
    "pc_qwq_32b": "qwen/qwq-32b"
}
DEFAULT_MODEL_ID = "mistralai/mistral-7b-instruct-v0.3"

def resolve_model_and_url(model_name: str = ""):
    """Traduit la clé du front-end en (URL_CIBLE, ID_LM_STUDIO)."""
    name = model_name.lower()
    target_url = MAC_URL if name.startswith("mac_") else PC_URL
    model_id = MODEL_MAP.get(name, DEFAULT_MODEL_ID)
    return target_url, model_id

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
        
    # Nettoyage des balises HTML parasites
    dispositif = re.sub(r'<[^>]+>', '', dispositif)
    expose = re.sub(r'<[^>]+>', '', expose)
    
    return {
        "auteur": auteur[:100], 
        "texte": f"Dispositif: {dispositif[:1000]}\nExposé: {expose[:500]}"
    }

# NOTE: La fonction analyser_doublons_identiques a été fusionnée dans 
# backend/app/main.py pour permettre l'interruption asynchrone (Bouton Stop).
