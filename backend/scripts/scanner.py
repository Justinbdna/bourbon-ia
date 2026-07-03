import json
import re
import os
import logging
import httpx
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
    "Va droit au but : contexte, article visé, risques, conclusion. N'extrapole jamais.\n"
    "RÈGLE ABSOLUE : Si l'outil de recherche de la base de données de l'Assemblée nationale ne renvoie aucun résultat pertinent, ne simule aucune information. "
    "Réponds exactement ceci : 'Je n'ai pas trouvé d'information correspondante dans la base de données. Pourriez-vous préciser le numéro de l'amendement ou de l'article s'il vous plaît ?'"
)

def call_mcp_tool(query: str) -> str:
    """Effectue un véritable appel HTTP POST au serveur MCP Tricoteuses."""
    mcp_path = os.path.join(os.path.dirname(__file__), "..", "mcp_config.json")
    try:
        with open(mcp_path, "r") as f:
            config = json.load(f)
        url = config["mcpServers"]["tricoteuses"]["url"]
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "recherche_base_parlementaire",
                "arguments": {"query": query}
            }
        }
        resp = httpx.post(url, json=payload, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
        if "result" in data and "content" in data["result"]:
            return data["result"]["content"][0].get("text", str(data["result"]))
        return str(data)
    except Exception as e:
        return f"Erreur de connexion au serveur MCP : {e}"


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
    logging.info(f"💬 Chat libre (stream/tools) — message reçu ({len(message)} car.) | Modèle résolu : {model_id} sur {target_url}")

    client = OpenAI(base_url=target_url, api_key="lm-studio", timeout=300.0)
    
    messages = [{"role": "user", "content": full_prompt}]
    tools = [{
        "type": "function",
        "function": {
            "name": "recherche_base_parlementaire",
            "description": "Recherche dans la base de données de l'Assemblée nationale (amendements, articles, lois).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "La requête de recherche (ex: 'réforme des retraites', numéro de l'amendement)."
                    }
                },
                "required": ["query"]
            }
        }
    }]

    try:
        print(f"🔗 Tentative de connexion au LLM sur l'URL : {target_url} | Modèle : {model_id} (Streaming & Tools)")
        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
            tools=tools if not context_text else None, # Pas besoin d'outil si le document est déjà fourni
            stream=True
        )
        
        is_tool_call = False
        tool_call_name = ""
        tool_call_args = ""
        tool_call_id = ""

        for chunk in response:
            delta = chunk.choices[0].delta
            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                is_tool_call = True
                tc = delta.tool_calls[0]
                if getattr(tc, 'id', None):
                    tool_call_id = tc.id
                if getattr(tc.function, 'name', None):
                    tool_call_name = tc.function.name
                if getattr(tc.function, 'arguments', None):
                    tool_call_args += tc.function.arguments
            elif hasattr(delta, 'content') and delta.content and not is_tool_call:
                yield delta.content

        if is_tool_call:
            yield f"\n\n> 🔍 *Appel de la base parlementaire MCP ({tool_call_name})...*\n\n"
            try:
                args = json.loads(tool_call_args)
                query = args.get("query", "")
                
                mcp_result = call_mcp_tool(query)
                
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": tool_call_name,
                            "arguments": tool_call_args
                        }
                    }]
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": tool_call_name,
                    "content": mcp_result
                })
                
                # Deuxième passe (streaming final)
                second_response = client.chat.completions.create(
                    model=model_id,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=2048,
                    stream=True
                )
                for chunk2 in second_response:
                    delta2 = chunk2.choices[0].delta
                    if hasattr(delta2, 'content') and delta2.content:
                        yield delta2.content
            except Exception as e:
                yield f"\n\n❌ L'outil a échoué: {str(e)}\n"

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
