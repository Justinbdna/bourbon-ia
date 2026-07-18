import json
import logging
import os
import re
import time
import asyncio
import html
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# GESTION DES IMPORTS POUR VERCEL SERVERLESS
# ==========================================
try:
    from api.sorting_engine import trier_amendements
except ModuleNotFoundError:
    from sorting_engine import trier_amendements

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
    provider: str = "groq"
    api_key: Optional[str] = None
    base_url: Optional[str] = None

class AnalyzeResult(BaseModel):
    id: str
    statut: str
    justification: str
    alerte_couleur: str
    rang: int = 0
    groupe: Optional[Dict[str, str]] = None

def normaliser_amendement(data, index: int = 0) -> dict:
    try:
        if not isinstance(data, dict):
            logging.warning(f"normaliser_amendement: entrée non-dict ignorée (type={type(data).__name__})")
            return {"id": f"amdt-{index}", "numero": "Inconnu", "article": "", "auteurs": [], "point_impact": {"type": ""}, "dispositif": "", "texte": "", "auteur": ""}
        
        # Selon le parsing frontend, l'objet peut être enveloppé par "amendement" ou l'être directement
        am = data.get("amendement", data)
        
        # On vérifie si c'est bien une structure de l'Assemblée (identification ou uid)
        if "identification" in am or "uid" in am or "pointeurFragmentTexte" in am:
            def safe_str(val, default=""):
                if isinstance(val, dict) and ("@xmlns" in val or "@xmlns:xsi" in val):
                    return "Non renseigné"
                if isinstance(val, (dict, list)):
                    import json
                    return json.dumps(val, ensure_ascii=False)
                res = str(val) if val is not None and str(val).strip() != "" else default
                return html.unescape(res)

            raw_numero = am.get("identification", {}).get("numeroLong", "Inconnu")
            numero = safe_str(raw_numero, "Inconnu")
            
            raw_article = am.get("pointeurFragmentTexte", {}).get("division", {}).get("titre", "")
            article = safe_str(raw_article)
            
            auteur = ""
            signataires = am.get("signataires", {})
            if isinstance(signataires, dict):
                auteur = safe_str(signataires.get("libelle", ""))
                if not auteur:
                    aut = signataires.get("auteur", {})
                    if isinstance(aut, dict):
                        auteur = safe_str(aut.get("acteurRef", "Inconnu"))
                    elif isinstance(aut, list) and len(aut) > 0:
                        auteur = safe_str(aut[0].get("acteurRef", "Inconnu"))
            else:
                auteur = safe_str(signataires)

            raw_impact = am.get("pointeurFragmentTexte", {}).get("division", {}).get("articleDesignation", "")
            impact = safe_str(raw_impact)
            
            corps = am.get("corps", {})
            raw_dispositif = corps.get("cartoucheInformatif")
            if not raw_dispositif:
                raw_dispositif = corps.get("contenuAuteur", {}).get("dispositif", "")
            dispositif = safe_str(raw_dispositif)
                
            raw_uid = am.get("uid", numero)
            uid = safe_str(raw_uid, numero)

            return {
                "id": uid or f"amdt-{index}",
                "numero": numero,
                "article": article,
                "auteurs": [auteur] if auteur else [],
                "point_impact": {"type": impact},
                "dispositif": dispositif,
                "texte": dispositif,
                "auteur": auteur
            }
            
        # Données déjà plates (ex: sampleAmendments.json)
        if not data.get("id"):
            data["id"] = f"amdt-{index}"
        return data
    except Exception as e:
        import traceback
        logging.error(f"Erreur de normalisation sur l'amendement {index}: {e}\n{traceback.format_exc()}")
        return {"id": f"amdt-err-{index}", "numero": "Erreur", "article": "", "auteurs": [], "point_impact": {"type": ""}, "dispositif": "", "texte": "", "auteur": ""}

@app.post("/api/normalize")
async def normalize_endpoint(payload: AnalyzeRequest):
    return [normaliser_amendement(a, i) for i, a in enumerate(payload.amendements)]

@app.post("/api/analyze", response_model=List[AnalyzeResult])
async def analyze_endpoint(raw_request: Request, payload: AnalyzeRequest):
    try:
        # 0. Normalisation des données brutes en données plates
        amendements_propres = [normaliser_amendement(a, i) for i, a in enumerate(payload.amendements)]

        # 1. Tri mécanique (Doctrine de l'Assemblée)
        amendements_tries = trier_amendements(amendements_propres)
    
        # Lazy Load OpenAI pour éviter les plantages au build
        from openai import AsyncOpenAI
        
        if payload.provider == "local":
            effective_base_url = payload.base_url or "http://localhost:1234/v1"
            effective_api_key = payload.api_key or "local-key"
            effective_model = "local-model"
        else:
            effective_base_url = "https://api.groq.com/openai/v1"
            effective_api_key = payload.api_key or os.getenv("GROQ_API_KEY")
            effective_model = "llama-3.3-70b-versatile"
            if not effective_api_key:
                logging.warning("Clé GROQ_API_KEY manquante.")
            
        client = AsyncOpenAI(
            base_url=effective_base_url, 
            api_key=effective_api_key or "DUMMY_KEY", 
            timeout=300.0
        )
        
        system_prompt = (
            "RÈGLE DE CLASSEMENT MVP : Tu es un administrateur de l'Assemblée nationale. Tu dois classer une liste d'amendements. Même si le 'dispositif' est vide, qu'il indique 'Non renseigné' ou 'Irrecevable au titre de l'article 40', TU DOIS LES CLASSER. \n"
            "- Si plusieurs amendements ciblent exactement le même 'article' et ont le même dispositif (même vide ou irrecevable), classe-les en 'Identiques'.\n"
            "- S'ils ciblent le même article mais diffèrent légèrement, classe-les en 'Discussion commune'.\n"
            "- Sinon, classe en 'Isolé'.\n"
            "Tu n'as pas le droit de renvoyer le statut 'Erreur' ou de refuser de classer. Tu dois trouver des corrélations logiques.\n"
            "RÈGLES DE FORMATAGE ABSOLUES ET INTRANSIGEANTES :\n"
            "1. Tu dois renvoyer un tableau JSON valide contenant EXACTEMENT un objet pour chaque amendement fourni.\n"
            "2. Tu DOIS conserver la valeur exacte de la clé 'id' de l'amendement (qui est une chaîne de caractères, ex: 'amdt-185', 'amdt-7rect', 'CD12'). Ne la remplace JAMAIS par un entier.\n"
            "3. La clé 'statut' ne peut avoir QUE l'une de ces 3 valeurs exactes : 'Identique', 'Discussion commune', ou 'Isolé'. Aucune autre valeur n'est tolérée (n'utilise pas 'Nouveau', ni 'Erreur').\n"
            "4. Voici le SEUL format JSON accepté en sortie. Tu dois le respecter à la lettre :\n"
            "[\n"
            "  {\n"
            "    \"id\": \"ID_EXACT_FOURNI_EN_ENTRÉE\",\n"
            "    \"statut\": \"Isolé\",\n"
            "    \"justification\": \"Ta justification courte ici\",\n"
            "    \"alerte_couleur\": \"gris\"\n"
            "  }\n"
            "]\n"
            "Ne rajoute aucune autre clé. Ne mets pas de texte avant ou après le tableau JSON."
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
        FALLBACK_MODELS = ["llama-3.1-8b-instant", "qwen/qwen3.6-27b", "llama-3.3-70b-versatile"]
        sem = asyncio.Semaphore(4)

        async def process_amendment(amend):
            async with sem:
                amend_id = str(amend.get("id", amend.get("numero", "Inconnu")))
                donnees_propres = amend
                
                user_prompt = (
                    f"REF - Auteur: {reference_brut.get('auteur', '')}\nTexte: {reference_brut.get('texte', '')}\n"
                    f"TEST - Auteur: {donnees_propres.get('auteur', '')}\nTexte: {donnees_propres.get('texte', '')}"
                )
                
                last_error = None
                for model_name in [effective_model]:
                    try:
                        response = await client.chat.completions.create(
                            model=model_name,
                            messages=[{"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}],
                            temperature=0.1,
                            max_tokens=200,
                        )
                        contenu = response.choices[0].message.content.strip()
                        logging.info(f"🚀 PROMPT GROQ:\n{system_prompt}\n\n{user_prompt}")
                        logging.info(f"✅ REPONSE BRUTE GROQ:\n{contenu}")
                        import re
                        raw_text = contenu.strip()
                        if raw_text.startswith("```"):
                            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                            raw_text = re.sub(r"\s*```$", "", raw_text)
                        contenu = raw_text.strip()
                            
                        json_match = re.search(r'\[.*\]|\{.*\}', contenu, re.DOTALL)
                        if json_match:
                            contenu = json_match.group(0)
                            
                        try:
                            data_json = json.loads(contenu)
                            if isinstance(data_json, list) and len(data_json) > 0:
                                data_json = data_json[0]
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
                        last_error = e
                        error_str = str(e).lower()
                        if "429" in error_str or "rate limit" in error_str or "quota" in error_str:
                            logging.warning(f"⚠️ Modèle {model_name} épuisé (429/Quota) sur l'amendement {amend_id}, passage au suivant...")
                        else:
                            logging.warning(f"⚠️ Modèle {model_name} a échoué sur l'amendement {amend_id} : {e}. Essai du suivant...")
                        continue

                logging.error(f"❌ ERREUR CRITIQUE LLM sur l'amendement {amend_id} : Tous les modèles ont échoué. Dernier : {last_error}")
                raise HTTPException(status_code=500, detail=f"Erreur API LLM (ex: Rate Limit 429). Les modèles de secours ont échoué : {str(last_error)}")

        # Création des tâches asynchrones pour tous les amendements sauf le premier
        tasks = [process_amendment(amend) for amend in amendements_tries[1:]]
        
        # Exécution parallèle avec concurrence contrôlée (semaphore = 4)
        resultats_paralleles = await asyncio.gather(*tasks)
        resultats.extend(resultats_paralleles)

        # Post-traitement : injection du rang et du groupe dans chaque résultat
        STATUT_TO_GROUPE = {
            "Identique": "identiques",
            "Identiques": "identiques",
            "Incompatible": "discussion_commune",
            "Discussion commune": "discussion_commune",
        }
        groupe_ids = {}
        final = []
        for i, r in enumerate(resultats):
            entry = r.model_dump() if hasattr(r, "model_dump") else r.dict()
            entry["rang"] = i + 1
            grp_type = STATUT_TO_GROUPE.get(entry["statut"])
            if grp_type:
                if grp_type not in groupe_ids:
                    groupe_ids[grp_type] = f"grp-{grp_type}-1"
                entry["groupe"] = {"type": grp_type, "groupe_id": groupe_ids[grp_type]}
            final.append(entry)
            
        return final
    except Exception as exc:
        logging.error("Erreur Backend", exc_info=True)
        return [{"id": am.get("id", f"fallback-{i}"), "statut": "Erreur", "justification": "Erreur de formatage du modèle.", "alerte_couleur": "rouge"} for i, am in enumerate(payload.amendements)]

@app.get("/api/health")
def health():
    return {"status": "ok"}

