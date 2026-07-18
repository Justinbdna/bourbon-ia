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
    amendements: list
    model: str = "mac_mistral"

class AnalyzeResult(BaseModel):
    id: str
    statut: str
    justification: str
    alerte_couleur: str

def normaliser_amendement(data: dict) -> dict:
    if "amendement" in data:
        am = data["amendement"]
        numero = am.get("identification", {}).get("numeroLong", "Inconnu")
        article = am.get("pointeurFragmentTexte", {}).get("division", {}).get("titre", "")
        auteur = am.get("signataires", {}).get("libelle", "")
        impact = am.get("pointeurFragmentTexte", {}).get("division", {}).get("articleDesignation", "")
        
        corps = am.get("corps", {})
        dispositif = corps.get("cartoucheInformatif")
        if not dispositif:
            disp_data = corps.get("contenuAuteur", {}).get("dispositif", "")
            dispositif = str(disp_data) if disp_data else ""
            
        uid = am.get("uid", numero)
        return {
            "id": uid,
            "numero": numero,
            "article": article,
            "auteurs": [auteur] if auteur else [],
            "point_impact": {"type": impact},
            "dispositif": dispositif,
            "texte": dispositif,
            "auteur": auteur
        }
    return data

@app.post("/api/normalize")
async def normalize_endpoint(payload: AnalyzeRequest):
    return [normaliser_amendement(a) for a in payload.amendements]

@app.post("/api/analyze", response_model=List[AnalyzeResult])
async def analyze_endpoint(raw_request: Request, payload: AnalyzeRequest):
    try:
        # 0. Normalisation des données brutes en données plates
        amendements_propres = [normaliser_amendement(a) for a in payload.amendements]

        # 1. Tri mécanique (Doctrine de l'Assemblée)
        amendements_tries = trier_amendements(amendements_propres)
    
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
        
        system_prompt = (
            "Tu es un assistant juridique. Compare ces amendements en ignorant le 'chapeau'. "
            "Réponds UNIQUEMENT en JSON avec les clés : id, statut (Doublon, Identique, Nouveau, Incompatible), justification."
        )
        
        if not amendements_tries:
            return []

        # Le premier amendement sert de référence absolue pour le lot
        # (les données sont déjà normalisées par notre fonction)
        reference_brut = amendements_tries[0]
        ref_id = str(reference_brut.get("id", reference_brut.get("numero", "Inconnu")))
        
        resultats = [AnalyzeResult(
            id=ref_id, 
            statut="Nouveau", 
            justification="Premier du lot (Référence globale).", 
            alerte_couleur="vert"
        )]
        
        sem = asyncio.Semaphore(4)

        async def process_amendment(amend):
            async with sem:
                amend_id = str(amend.get("id", amend.get("numero", "Inconnu")))
                donnees_propres = amend
                
                user_prompt = (
                    f"REF - Auteur: {reference_brut.get('auteur', '')}\nTexte: {reference_brut.get('texte', '')}\n"
                    f"TEST - Auteur: {donnees_propres.get('auteur', '')}\nTexte: {donnees_propres.get('texte', '')}"
                )
                
                try:
                    response = await client.chat.completions.create(
                        model="llama3-8b-8192",
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
                        
                    return AnalyzeResult(
                        id=amend_id, 
                        statut=statut,
                        justification=data_json.get("justification", ""),
                        alerte_couleur=couleur
                    )
                        
                except Exception as e:
                    logging.error(f"❌ ERREUR LLM sur l'amendement {amend_id} : {e}")
                    raise HTTPException(status_code=500, detail=f"Erreur API LLM (ex: Rate Limit 429) : {str(e)}")

        # Création des tâches asynchrones pour tous les amendements sauf le premier
        tasks = [process_amendment(amend) for amend in amendements_tries[1:]]
        
        # Exécution parallèle avec concurrence contrôlée (semaphore = 4)
        resultats_paralleles = await asyncio.gather(*tasks)
        resultats.extend(resultats_paralleles)
            
        return resultats
    except Exception as exc:
        logging.error("Erreur Backend", exc_info=True)
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/api/health")
def health():
    return {"status": "ok"}

