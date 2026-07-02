"""
Bourbon.IA — Serveur FastAPI
API REST locale pour le MVP du hackathon.

Endpoints :
  GET  /api/amendements       → Liste les amendements nettoyés
  POST /api/scan              → Scanne un amendement via le LLM local
"""
import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.scripts.scanner import resumer_amendement

# --- Configuration ---
DATA_CLEAN = Path(__file__).resolve().parent.parent.parent / "data" / "clean" / "amendements_clean.json"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# --- Chargement des données au démarrage ---
def charger_amendements() -> list[dict]:
    """Charge les amendements nettoyés depuis le JSON. Appelé une seule fois au boot."""
    if not DATA_CLEAN.is_file():
        logging.error(f"Fichier de données introuvable : {DATA_CLEAN}")
        logging.error("Lance d'abord : python3 backend/scripts/parser.py --input-dir data/raw/DLR5L11N19503 --output data/clean/amendements_clean.json")
        return []

    try:
        with open(DATA_CLEAN, "r", encoding="utf-8") as f:
            data = json.load(f)
        logging.info(f"{len(data)} amendements chargés depuis {DATA_CLEAN.name}")
        return data
    except (json.JSONDecodeError, OSError) as e:
        logging.error(f"Erreur chargement données : {e}")
        return []


# --- Application FastAPI ---
app = FastAPI(
    title="Bourbon.IA",
    description="Assistant législatif 100% local — API du hackathon AN 2026",
    version="0.1.0",
)

# CORS : autorise le front-end React (Vite tourne sur le port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Données chargées en mémoire au démarrage
AMENDEMENTS: list[dict] = charger_amendements()


# --- Modèles Pydantic ---
class ScanRequest(BaseModel):
    """Corps de la requête POST /api/scan."""
    numero: str  # Numéro (uid) de l'amendement à scanner


class ScanResponse(BaseModel):
    """Réponse du scanner LLM."""
    numero: str
    resume: str
    comparatif: str
    enjeux_politiques: str
    points_de_vigilance: str
    source: str


# --- Endpoints ---
@app.get("/api/amendements")
def lister_amendements(limit: int = 20, offset: int = 0):
    """
    Retourne la liste paginée des amendements nettoyés.
    
    Query params :
      - limit  : nombre d'amendements par page (défaut 20, max 100)
      - offset : position de départ (défaut 0)
    """
    limit = min(limit, 100)  # Cap à 100 pour ne pas surcharger
    page = AMENDEMENTS[offset : offset + limit]

    return {
        "total": len(AMENDEMENTS),
        "limit": limit,
        "offset": offset,
        "amendements": page,
    }


@app.post("/api/scan", response_model=ScanResponse)
def scanner_amendement(request: ScanRequest):
    """
    Scanne un amendement par son numéro via le LLM local.
    
    Body JSON : { "numero": "AMANR5L17PO59051B0149P0D1N000001" }
    """
    print(f"📥 Requête reçue pour l'amendement n° {request.numero}")
    
    # 1. Trouver l'amendement dans les données chargées
    amendement = None
    for am in AMENDEMENTS:
        if am.get("numero") == request.numero:
            amendement = am
            break

    if not amendement:
        print("🔍 Recherche dans la base... (Non trouvé)")
        raise HTTPException(
            status_code=404,
            detail=f"Amendement '{request.numero}' introuvable dans les {len(AMENDEMENTS)} amendements chargés."
        )
        
    print("🔍 Recherche dans la base... (Trouvé)")
    print("🧠 Envoi du texte à Mistral (LM Studio)...")

    # 2. Envoyer au LLM via scanner.py
    resultat = resumer_amendement(amendement)

    if not resultat:
        raise HTTPException(
            status_code=502,
            detail="Le LLM local n'a pas répondu. Vérifiez que LM Studio est démarré avec un modèle chargé."
        )

    print("✅ Résumé généré avec succès !")
    return ScanResponse(**resultat)


# --- Health check ---
@app.get("/api/health")
def health():
    """Vérifie que l'API est vivante et que les données sont chargées."""
    return {
        "status": "ok",
        "amendements_charges": len(AMENDEMENTS),
        "data_source": str(DATA_CLEAN.name),
    }
