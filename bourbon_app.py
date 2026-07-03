"""
Bourbon.IA — Application backend tout-en-un (version consolidée exécutable)
===========================================================================
Regroupe en un seul fichier : configuration, client LLM, client MCP,
logique du Scanner, et l'API FastAPI. Pratique pour un lancement rapide
en hackathon (aucun découpage en modules requis).

Corrige les 3 problèmes de la version d'origine :
  1. resumer_amendement() honore désormais la sélection de modèle.
  2. Gestion d'erreur réelle du SDK OpenAI (openai.APIConnectionError,
     APITimeoutError) au lieu du ConnectionError builtin (jamais levé).
  3. Config centralisée et pilotable via .env (LLM + MCP_URL configurable).

Lancement :
  pip install -r backend/requirements.txt
  cp .env.example .env          # puis ajustez LLM_API_URL / MCP_URL

  # Option A — directement :
  python3 bourbon_app.py

  # Option B — via uvicorn (rechargement à chaud) :
  uvicorn bourbon_app:app --reload
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

import httpx
import openai
from openai import OpenAI

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Charger .env AVANT de lire la moindre variable d'environnement.
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("bourbon")


# ==========================================================================
# 1. CONFIGURATION  (tout est pilotable via .env)
# ==========================================================================
LLM_LOCAL_URL = os.environ.get("LLM_LOCAL_URL", "http://127.0.0.1:1234/v1")
LLM_REMOTE_URL = os.environ.get("LLM_API_URL", "http://127.0.0.1:1234/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "lm-studio")  # factice pour LM Studio
LLM_TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "300"))

# MCP configurable — plus de hardcode. Fallback : fichier mcp_config.json.
MCP_URL = os.environ.get("MCP_URL", "")

DEFAULT_MODEL_ID = "mistralai/mistral-7b-instruct-v0.3"

# clé front-end → (emplacement, id LM Studio). Une seule source de vérité.
MODEL_MAP: dict[str, tuple[str, str]] = {
    "mac_mistral":   ("local",  "mistralai/mistral-7b-instruct-v0.3"),
    "mac_llama":     ("local",  "lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF"),
    "mac_qwen":      ("local",  "qwen/qwen3.5-9b"),
    "mac_gemma":     ("local",  "google/gemma-4-e2b"),
    "pc_mistral_7b": ("remote", "mistralai/mistral-7b-instruct-v0.3"),
    "pc_mistral_14b":("remote", "mistralai/ministral-3-14b-reasoning"),
    "pc_gemma_12b":  ("remote", "google/gemma-4-12b"),
    "pc_qwen_35b":   ("remote", "qwen/qwen3.6-35b-a3b"),
    "pc_qwq_32b":    ("remote", "qwen/qwq-32b"),
}

# Chemins (relatifs à l'emplacement de CE fichier = racine du dépôt).
ROOT = Path(__file__).resolve().parent
DATA_CLEAN = ROOT / "data" / "clean" / "amendements_clean.json"
MCP_CONFIG = ROOT / "backend" / "mcp_config.json"


def resolve_model(model_name: str = "") -> tuple[str, str]:
    """clé front-end → (url_cible, id_modele). Utilisée par TOUTES les fonctions LLM."""
    where, model_id = MODEL_MAP.get(model_name.lower(), ("remote", DEFAULT_MODEL_ID))
    url = LLM_LOCAL_URL if where == "local" else LLM_REMOTE_URL
    return url, model_id


def get_mcp_url() -> str:
    """URL du serveur MCP : priorité à l'env MCP_URL, sinon mcp_config.json."""
    if MCP_URL:
        return MCP_URL
    try:
        with open(MCP_CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)["mcpServers"]["tricoteuses"]["url"]
    except (OSError, KeyError, json.JSONDecodeError) as e:
        log.warning(f"Config MCP introuvable/invalide : {e}")
        return ""


# ==========================================================================
# 2. CLIENT LLM  (une seule fabrique de client + gestion d'erreur correcte)
# ==========================================================================
class LLMUnavailable(Exception):
    """Le serveur LLM ne répond pas — remonté proprement à la couche API."""


def _client(url: str) -> OpenAI:
    return OpenAI(base_url=url, api_key=LLM_API_KEY, timeout=LLM_TIMEOUT)


def llm_chat(messages: list[dict], model_name: str = "", **kw) -> str:
    """Appel synchrone ; retourne le texte de la réponse."""
    url, model_id = resolve_model(model_name)
    log.info(f"🔗 LLM {model_id} @ {url}")
    try:
        resp = _client(url).chat.completions.create(model=model_id, messages=messages, **kw)
        return resp.choices[0].message.content or ""
    except (openai.APIConnectionError, openai.APITimeoutError) as e:
        # NB : le SDK OpenAI ne lève PAS le ConnectionError builtin.
        log.error(f"❌ LLM injoignable @ {url} (pare-feu / Tailscale ?) : {e}")
        raise LLMUnavailable(str(e)) from e


def llm_chat_raw(messages: list[dict], model_name: str = "", **kw):
    """Appel synchrone renvoyant l'objet message complet (pour les tool_calls)."""
    url, model_id = resolve_model(model_name)
    try:
        resp = _client(url).chat.completions.create(model=model_id, messages=messages, **kw)
        return resp.choices[0].message
    except (openai.APIConnectionError, openai.APITimeoutError) as e:
        log.error(f"❌ LLM injoignable @ {url} : {e}")
        raise LLMUnavailable(str(e)) from e


def llm_chat_stream(messages: list[dict], model_name: str = "", **kw):
    """Générateur de chunks de texte (streaming)."""
    url, model_id = resolve_model(model_name)
    try:
        stream = _client(url).chat.completions.create(
            model=model_id, messages=messages, stream=True, **kw
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
    except (openai.APIConnectionError, openai.APITimeoutError) as e:
        log.error(f"❌ LLM injoignable @ {url} : {e}")
        yield f"❌ Erreur : LLM local injoignable ({e})."


# ==========================================================================
# 3. CLIENT MCP  (sourçage base parlementaire)
# ==========================================================================
def call_mcp_tool(query: str) -> str:
    """Appel HTTP POST (JSON-RPC) au serveur MCP Tricoteuses."""
    url = get_mcp_url()
    if not url:
        return "Erreur : aucun serveur MCP configuré."
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "recherche_base_parlementaire", "arguments": {"query": query}},
    }
    try:
        resp = httpx.post(url, json=payload, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
        if "result" in data and "content" in data["result"]:
            return data["result"]["content"][0].get("text", str(data["result"]))
        return str(data)
    except Exception as e:  # httpx.HTTPError, JSON, etc.
        return f"Erreur de connexion au serveur MCP : {e}"


# ==========================================================================
# 4. LOGIQUE MÉTIER — LE SCANNER
# ==========================================================================
SYSTEM_PROMPT = (
    "Tu es un administrateur chevronné de l'Assemblée nationale française, expert en droit "
    "constitutionnel. Ton rôle est de décrypter les amendements pour les parlementaires. "
    "Tu dois être ultra-concis, neutre, et utiliser un vocabulaire juridique irréprochable. "
    "Ne fais aucune phrase d'introduction."
)

CHAT_SYSTEM_PROMPT = (
    "Tu agis comme un outil d'analyse juridique de pointe. Ta réponse doit être structurée avec "
    "des puces (bullet points) percutantes. Va droit au but : contexte, article visé, risques, "
    "conclusion. N'extrapole jamais.\n"
    "RÈGLE ABSOLUE : Si l'outil de recherche de la base de données de l'Assemblée nationale ne "
    "renvoie aucun résultat pertinent, ne simule aucune information. Réponds exactement ceci : "
    "'Je n'ai pas trouvé d'information correspondante dans la base de données. Pourriez-vous "
    "préciser le numéro de l'amendement ou de l'article s'il vous plaît ?'"
)


def _extract_json(contenu: str) -> dict | None:
    """Extrait un objet JSON, même s'il est encapsulé dans un bloc markdown ```json."""
    if not contenu or not contenu.strip():
        return None
    propre = contenu.strip()
    match = re.search(r"```(?:json)?(.*?)```", propre, re.DOTALL | re.IGNORECASE)
    if match:
        propre = match.group(1).strip()
    try:
        return json.loads(propre)
    except json.JSONDecodeError as e:
        log.error(f"JSON invalide renvoyé par le LLM : {e}\nBrut : {contenu[:300]}")
        return None


def _build_scan_prompt(am: dict) -> str:
    numero = am.get("numero", "Inconnu")
    user_prompt = (
        f"Voici l'amendement n°{numero} :\n\n"
        f"**Auteur** : {am.get('auteur', 'Non renseigné')}\n\n"
        f"**Dispositif (texte de loi modifié)** :\n{am.get('texte', 'Non disponible')}\n\n"
        f"**Exposé des motifs** :\n{am.get('motif', 'Non disponible')}\n\n"
        "Exigence stricte : ta réponse DOIT être un objet JSON valide avec EXACTEMENT ces 4 clés :\n"
        "- \"resume\" (Explication claire de l'action de l'amendement, max 2 phrases)\n"
        "- \"comparatif\" (Ce que l'amendement MODIFIE, AJOUTE ou SUPPRIME vs la loi initiale)\n"
        "- \"enjeux_politiques\" (L'impact réel et les débats potentiels générés)\n"
        "- \"points_de_vigilance\" (Risques constitutionnels ou budgétaires, type Article 40)"
    )
    # Mistral 7B n'accepte que user/assistant → on injecte le système en tête.
    return f"[INSTRUCTION SYSTÈME] {SYSTEM_PROMPT}\n\n[REQUÊTE]\n{user_prompt}"


def resumer_amendement(am: dict, model_name: str = "") -> dict | None:
    """Résume un amendement via le LLM. Honore désormais model_name."""
    numero = am.get("numero", "Inconnu")
    messages = [{"role": "user", "content": _build_scan_prompt(am)}]
    try:
        contenu = llm_chat(messages, model_name=model_name, temperature=0.3, max_tokens=512)
    except LLMUnavailable:
        return None

    data = _extract_json(contenu)
    if data is None:
        return None

    return {
        "numero": numero,
        "resume": data.get("resume", "Non renseigné"),
        "comparatif": data.get("comparatif", "Non renseigné"),
        "enjeux_politiques": data.get("enjeux_politiques", "Non renseigné"),
        "points_de_vigilance": data.get("points_de_vigilance", "Aucun"),
        "source": f"Amendement n°{numero}",
    }


def chat_libre(message: str, context_text: str = "", model_name: str = ""):
    """Chat conversationnel (streaming), avec appel MCP optionnel."""
    user_content = message
    if context_text:
        user_content = (
            f"{message}\n\n--- DOCUMENT FOURNI ---\n{context_text}\n--- FIN DU DOCUMENT ---"
        )
    full_prompt = f"[INSTRUCTION SYSTÈME] {CHAT_SYSTEM_PROMPT}\n\n[REQUÊTE]\n{user_content}"
    messages: list[dict] = [{"role": "user", "content": full_prompt}]

    tools = [{
        "type": "function",
        "function": {
            "name": "recherche_mcp",
            "description": "Recherche dans la base de données de l'Assemblée nationale",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "La requête (ex: 'réforme des retraites', numéro d'amendement).",
                    }
                },
                "required": ["query"],
            },
        },
    }]

    try:
        # Étape 1 : le LLM décide s'il veut un outil (pas d'outil si un doc est fourni).
        msg = llm_chat_raw(
            messages, model_name=model_name, temperature=0.3, max_tokens=2048,
            tools=tools if not context_text else None,
        )
    except LLMUnavailable as e:
        yield f"❌ Erreur : LLM local injoignable ({e})."
        return

    if msg.tool_calls:
        tool_call = msg.tool_calls[0]
        query = ""
        if tool_call.function.arguments:
            try:
                query = json.loads(tool_call.function.arguments).get("query", "")
            except json.JSONDecodeError:
                pass

        yield f"\n\n> 🔍 *Appel de la base parlementaire MCP pour : {query}...*\n\n"
        mcp_result = call_mcp_tool(query)

        messages.append(msg)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_call.function.name,
            "content": mcp_result,
        })

    # Étape 2 : réponse finale en streaming (avec ou sans résultat d'outil).
    yield from llm_chat_stream(messages, model_name=model_name, temperature=0.3, max_tokens=2048)


# ==========================================================================
# 5. CHARGEMENT DES DONNÉES
# ==========================================================================
def charger_amendements() -> list[dict]:
    """Charge les amendements nettoyés depuis le JSON (une fois au démarrage)."""
    if not DATA_CLEAN.is_file():
        log.error(f"Fichier de données introuvable : {DATA_CLEAN}")
        log.error(
            "Lance d'abord : python3 backend/scripts/parser.py "
            "--input-dir data/raw/<DOSSIER> --output data/clean/amendements_clean.json"
        )
        return []
    try:
        with open(DATA_CLEAN, "r", encoding="utf-8") as f:
            data = json.load(f)
        log.info(f"{len(data)} amendements chargés depuis {DATA_CLEAN.name}")
        return data
    except (json.JSONDecodeError, OSError) as e:
        log.error(f"Erreur chargement données : {e}")
        return []


AMENDEMENTS: list[dict] = charger_amendements()


# ==========================================================================
# 6. API FastAPI
# ==========================================================================
app = FastAPI(
    title="Bourbon.IA",
    description="Assistant législatif souverain — API du hackathon AN 2026",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScanRequest(BaseModel):
    numero: str
    model: str = ""  # sélection de modèle optionnelle (désormais respectée)


class ScanResponse(BaseModel):
    numero: str
    resume: str
    comparatif: str
    enjeux_politiques: str
    points_de_vigilance: str
    source: str


class ChatRequest(BaseModel):
    message: str
    context_text: str = ""
    model: str = "pc_mistral_7b"


@app.get("/api/amendements")
def lister_amendements(limit: int = 20, offset: int = 0):
    limit = min(limit, 100)
    return {
        "total": len(AMENDEMENTS),
        "limit": limit,
        "offset": offset,
        "amendements": AMENDEMENTS[offset : offset + limit],
    }


@app.post("/api/scan", response_model=ScanResponse)
def scanner_amendement(request: ScanRequest):
    amendement = next((am for am in AMENDEMENTS if am.get("numero") == request.numero), None)
    if not amendement:
        raise HTTPException(
            404,
            f"Amendement '{request.numero}' introuvable dans les {len(AMENDEMENTS)} chargés.",
        )
    log.info(f"🧠 Scan de l'amendement n°{request.numero}...")
    resultat = resumer_amendement(amendement, model_name=request.model)
    if not resultat:
        raise HTTPException(
            502, "Le LLM local n'a pas répondu ou a renvoyé un format invalide."
        )
    return ScanResponse(**resultat)


@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    log.info(f"💬 Chat | modèle={request.model} | contexte={len(request.context_text)} car.")

    def event_stream():
        for chunk in chat_libre(request.message, request.context_text, request.model):
            if chunk:
                yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "amendements_charges": len(AMENDEMENTS),
        "data_source": DATA_CLEAN.name,
        "mcp_url": get_mcp_url() or "non configuré",
    }


# ==========================================================================
# 7. POINT D'ENTRÉE
# ==========================================================================
if __name__ == "__main__":
    import uvicorn

    log.info("🚀 Démarrage de Bourbon.IA sur http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
