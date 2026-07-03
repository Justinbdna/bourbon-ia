import json
import re
import os
import logging
from dotenv import load_dotenv
from openai import OpenAI

# Charger les variables d'environnement depuis .env AVANT toute utilisation
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# --- Configuration LM Studio ---
# L'URL du PC distant est récupérée depuis le fichier .env
PC_URL = os.environ.get("LLM_API_URL", "http://100.78.180.81:1234/v1")
MAC_URL = "http://127.0.0.1:1234/v1"

# --- Mapping des modèles commerciaux → ID LM Studio ---
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
    
    # Routage
    target_url = MAC_URL if name.startswith("mac_") else PC_URL
    
    # Mapping exact
    model_id = MODEL_MAP.get(name, DEFAULT_MODEL_ID)
    
    return target_url, model_id

SYSTEM_PROMPT = (
    "Tu es un administrateur chevronné de l'Assemblée nationale française, expert en droit constitutionnel. "
    "Ton rôle est de décrypter les amendements pour les parlementaires. "
    "Tu dois être ultra-concis, neutre, et utiliser un vocabulaire juridique irréprochable. "
    "Ne fais aucune phrase d'introduction."
)


def resumer_amendement(amendement_clean: dict) -> dict:
    """
    Envoie un amendement nettoyé au LLM local et retourne un résumé structuré.
    
    Args:
        amendement_clean: dict issu de parser.clean_amendement()
            Clés attendues : numero, auteur, texte, motif
    
    Returns:
        dict avec les clés : numero, resume, enjeux, source
        ou None en cas d'erreur.
    """
    numero = amendement_clean.get("numero", "Inconnu")

    # Construction du prompt utilisateur
    user_prompt = (
        f"Voici l'amendement n°{numero} :\n\n"
        f"**Auteur** : {amendement_clean.get('auteur', 'Non renseigné')}\n\n"
        f"**Dispositif (texte de loi modifié)** :\n{amendement_clean.get('texte', 'Non disponible')}\n\n"
        f"**Exposé des motifs** :\n{amendement_clean.get('motif', 'Non disponible')}\n\n"
        "Exigence stricte : ta réponse DOIT être un objet JSON valide avec EXACTEMENT ces 4 clés :\n"
        "- \"resume\" (Explication claire de l'action de l'amendement, max 2 phrases)\n"
        "- \"comparatif\" (Explication explicite de ce que l'amendement MODIFIE, AJOUTE ou SUPPRIME par rapport à la loi initiale)\n"
        "- \"enjeux_politiques\" (L'impact réel et les débats potentiels générés)\n"
        "- \"points_de_vigilance\" (Risques constitutionnels ou budgétaires, type Article 40)"
    )

    logging.info(f"Envoi de l'amendement n°{numero} au LLM...")

    try:
        # Mistral 7B Instruct n'accepte que user/assistant dans son template Jinja.
        # On injecte le rôle système en tête du message utilisateur.
        full_prompt = f"[INSTRUCTION SYSTÈME] {SYSTEM_PROMPT}\n\n[REQUÊTE]\n{user_prompt}"

        model_id = DEFAULT_MODEL_ID
        client = OpenAI(base_url=PC_URL, api_key="lm-studio", timeout=300.0)
        
        print(f"🔗 Tentative de connexion au LLM sur l'URL : {PC_URL} | Modèle : {model_id}")
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "user", "content": full_prompt},
            ],
            temperature=0.3,  # Bas pour rester factuel
            max_tokens=512,
        )
    except ConnectionError:
        logging.error(f"❌ Connexion refusée sur {PC_URL}. Vérifiez le pare-feu Windows et Tailscale.")
        return None
    except Exception as e:
        logging.error(f"❌ Erreur lors de l'appel au LLM ({PC_URL}) : {e}")
        return None

    # Extraire la réponse
    contenu = response.choices[0].message.content
    if not contenu or not contenu.strip():
        logging.warning(f"Réponse vide du LLM pour l'amendement n°{numero}.")
        return None

    # Sécurisation du parsing JSON (fallback si markdown)
    contenu_propre = contenu.strip()
    match = re.search(r"```(?:json)?(.*?)```", contenu_propre, re.DOTALL | re.IGNORECASE)
    if match:
        contenu_propre = match.group(1).strip()

    try:
        data_json = json.loads(contenu_propre)
    except json.JSONDecodeError as e:
        logging.error(f"Le LLM n'a pas renvoyé un JSON valide pour l'amendement n°{numero} : {e}\nContenu brut : {contenu}")
        return None

    logging.info(f"Résumé reçu pour l'amendement n°{numero}.")

    return {
        "numero": numero,
        "resume": data_json.get("resume", "Non renseigné"),
        "comparatif": data_json.get("comparatif", "Non renseigné"),
        "enjeux_politiques": data_json.get("enjeux_politiques", "Non renseigné"),
        "points_de_vigilance": data_json.get("points_de_vigilance", "Aucun"),
        "source": f"Amendement n°{numero}",
    }


CHAT_SYSTEM_PROMPT = (
    "Tu agis comme un outil d'analyse juridique de pointe. Ta réponse doit être structurée avec des puces (bullet points) percutantes. "
    "Va droit au but : contexte, article visé, risques, conclusion. N'extrapole jamais."
)


def chat_libre(message: str, context_text: str = "", model_name: str = ""):
    """
    Mode conversationnel libre avec le LLM local (Streaming).
    """
    user_content = message
    if context_text:
        user_content = (
            f"{message}\n\n"
            f"--- DOCUMENT FOURNI ---\n"
            f"{context_text}\n"
            f"--- FIN DU DOCUMENT ---"
        )

    full_prompt = f"[INSTRUCTION SYSTÈME] {CHAT_SYSTEM_PROMPT}\n\n[REQUÊTE]\n{user_content}"

    target_url, model_id = resolve_model_and_url(model_name)
    logging.info(f"💬 Chat libre (stream) — message reçu ({len(message)} car.) | Modèle résolu : {model_id} sur {target_url}")

    client = OpenAI(base_url=target_url, api_key="lm-studio", timeout=300.0)

    try:
        print(f"🔗 Tentative de connexion au LLM sur l'URL : {target_url} | Modèle : {model_id} (Streaming)")
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "user", "content": full_prompt},
            ],
            temperature=0.3,
            max_tokens=2048,
            stream=True
        )
        
        for chunk in response:
            if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except ConnectionError:
        logging.error(f"❌ Connexion refusée sur {target_url}. Vérifiez le pare-feu Windows et Tailscale.")
        yield "❌ Erreur : Connexion refusée."
    except Exception as e:
        logging.error(f"❌ Erreur lors de l'appel chat au LLM ({target_url}) : {e}")
        yield f"❌ Erreur lors de la génération : {str(e)}"


if __name__ == "__main__":
    # Test rapide avec un amendement factice
    test_amendement = {
        "numero": "CL42",
        "auteur": "Mme Dupont",
        "texte": "À l'article 3, remplacer les mots « deux ans » par les mots « trois ans ».",
        "motif": "Cet amendement vise à allonger le délai de prescription afin de mieux protéger les victimes.",
    }

    resultat = resumer_amendement(test_amendement)
    if resultat:
        print("\n" + "=" * 50)
        print("RÉSULTAT DU SCANNER")
        print("=" * 50)
        print(f"\n📌 Résumé : {resultat['resume']}")
        print(f"🔄 Comparatif : {resultat['comparatif']}")
        print(f"🏛️ Enjeux : {resultat['enjeux_politiques']}")
        print(f"⚠️ Vigilance : {resultat['points_de_vigilance']}")
        print(f"🔗 Source : {resultat['source']}")
    else:
        print("❌ Le scan a échoué.")
