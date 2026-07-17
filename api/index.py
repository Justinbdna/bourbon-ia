import json
import logging
import os
import re
import time
import asyncio
from typing import List, Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# GESTION DES IMPORTS POUR VERCEL SERVERLESS
# ==========================================
try:
    # Environnement Vercel (depuis la racine du projet)
    from api.sorting_engine import trier_amendements
    from api.llm_processor import extraire_texte_brut
except ModuleNotFoundError:
    # Environnement Local (exécution directe dans le dossier api/)
    from sorting_engine import trier_amendements
    from llm_processor import extraire_texte_brut

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

app = FastAPI(
    title="Bourbon.IA",
    description="Assistant législatif 100% local — API du hackathon AN 2026",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permettre toutes les origines pour le Vercel Serverless
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    amendements: List[Dict[str, Any]]
    model: str = "mac_mistral"

class AnalyzeResult(BaseModel):
    id: str
    statut: str
    justification: str
    alerte_couleur: str

@app.post("/api/analyze", response_model=List[AnalyzeResult])
async def analyze_endpoint(raw_request: Request, payload: AnalyzeRequest):
    try:
        # 1. Tri mécanique (Doctrine de l'Assemblée)
        amendements_tries = trier_amendements(payload.amendements)
    
        # Lazy Load OpenAI pour éviter les plantages au build
        from openai import AsyncOpenAI
        
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logging.warning("Clé GROQ_API_KEY manquante. L'analyse LLM risque d'échouer.")
            
        client = AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1", 
            api_key=api_key or "DUMMY_KEY", 
            timeout=300.0
        )
        
        resultats = []
        amendement_precedent = None
        
        system_prompt = (
            "Tu es un assistant juridique. Compare ces amendements en ignorant le 'chapeau'. "
            "Réponds UNIQUEMENT en JSON avec les clés : id, statut (Doublon, Identique, Nouveau, Incompatible), justification."
        )
        
        for amend in amendements_tries:
            # Vérifie si le front-end a cliqué sur "Stop"
            if await raw_request.is_disconnected():
                logging.warning("🛑 Analyse interrompue par le client.")
                break
                
            amend_id = str(amend.get("id", amend.get("numero", "Inconnu")))
            donnees_propres = extraire_texte_brut(amend)
            
            if amendement_precedent is None:
                resultats.append(AnalyzeResult(
                    id=amend_id, 
                    statut="Nouveau", 
                    justification="Premier du lot (Référence).", 
                    alerte_couleur="vert"
                ))
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
                    
                resultats.append(AnalyzeResult(
                    id=amend_id, 
                    statut=statut,
                    justification=data_json.get("justification", ""),
                    alerte_couleur=couleur
                ))
                
                if statut == "Nouveau":
                    amendement_precedent = donnees_propres
                    
            except Exception as e:
                logging.error(f"❌ ERREUR LLM sur l'amendement {amend_id} : {e}")
                await asyncio.sleep(1)
                resultats.append(AnalyzeResult(
                    id=amend_id, 
                    statut="Erreur",
                    justification=str(e), 
                    alerte_couleur="rouge"
                ))
            
        return resultats
    except Exception as exc:
        logging.error("Erreur Backend", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/health")
def health():
    return {"status": "ok"}

