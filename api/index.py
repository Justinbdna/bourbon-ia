"""
Bourbon.IA — Serveur FastAPI
API REST locale pour le MVP du hackathon.
"""
import json
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from api.sorting_engine import trier_amendements

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

app = FastAPI(
    title="Bourbon.IA",
    description="Assistant législatif 100% local — API du hackathon AN 2026",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    amendements: list[dict]
    model: str = "mac_mistral"

class AnalyzeResult(BaseModel):
    id: str
    statut: str
    justification: str
    alerte_couleur: str

@app.post("/api/analyze", response_model=list[AnalyzeResult])
async def analyze_endpoint(raw_request: Request, payload: AnalyzeRequest):
    """
    Contrat de Données Front/Back (Yassine).
    Reçoit un tableau d'amendements bruts et retourne pour chacun son statut structuré.
    """
    # 1. Tri mécanique (Doctrine de l'Assemblée)
    amendements_tries = trier_amendements(payload.amendements)
    
    # 2. Analyse LLM par lots (avec vérification d'interruption du front-end)
    # L'implémentation originelle dans llm_processor.py était synchrone, 
    # mais puisque nous devons gérer raw_request.is_disconnected() à chaque itération, 
    # la boucle logique a été adaptée pour permettre l'interruption.
    from api.llm_processor import extraire_texte_brut
    from openai import AsyncOpenAI
    import re
    import time
    import asyncio
    import os
    
    client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=os.getenv("GROQ_API_KEY"), timeout=300.0)
    
    resultats = []
    amendement_precedent = None
    
    system_prompt = (
        "Tu es un assistant juridique. Compare ces amendements en ignorant le 'chapeau'. "
        "Réponds UNIQUEMENT en JSON avec les clés : id, statut (Doublon, Identique, Nouveau, Incompatible), justification."
    )
    
    for amend in amendements_tries:
        # Vérifie si le front-end a cliqué sur "Stop"
        if await raw_request.is_disconnected():
            logging.warning("🛑 Analyse interrompue par le client (Bouton Stop).")
            break
            
        amend_id = amend.get("id", amend.get("numero", "Inconnu"))
        donnees_propres = extraire_texte_brut(amend)
        
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
            response = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}],
                temperature=0.1,
                max_tokens=200,
            )
            contenu = response.choices[0].message.content.strip()
            match = re.search(r"```(?:json)?(.*?)```", contenu, re.DOTALL | re.IGNORECASE)
            if match:
                contenu = match.group(1).strip()
                
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
            print(f"❌ ERREUR LLM sur l'amendement {amend_id} : {e}")
            await asyncio.sleep(1)  # Laisse LM Studio respirer
            resultats.append({
                "id": amend_id, "statut": "Erreur",
                "justification": str(e), "alerte_couleur": "rouge"
            })
            
    return resultats

@app.get("/api/health")
def health():
    return {"status": "ok"}
