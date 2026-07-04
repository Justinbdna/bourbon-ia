import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers.classify import router as classify_router

logging.basicConfig(level=logging.INFO)

settings = get_settings()

app = FastAPI(
    title="API de classement des amendements — Assemblée nationale",
    description=(
        "Backend interne dédié au classement automatique d'amendements législatifs "
        "via l'IA Mistral, selon les règles de classement de l'Assemblée nationale. "
        "Ne traite aucune autre tâche."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(classify_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "modele": settings.MISTRAL_MODEL}
