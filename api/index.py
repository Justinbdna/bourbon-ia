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

# ── Imports V2 (Pipeline enrichi) ──
try:
    from api.deterministic_engine import process_deterministic_sorting, normalize_text
    from api.schemas import EnrichedAmendment, StatutMecanique
    from api.llm_semantic_engine import evaluate_similitude
    from api.cache_manager import get_cached_classification, save_classification
except ModuleNotFoundError:
    from deterministic_engine import process_deterministic_sorting, normalize_text
    from schemas import EnrichedAmendment, StatutMecanique
    from llm_semantic_engine import evaluate_similitude
    from cache_manager import get_cached_classification, save_classification

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

app = FastAPI(
    title="Bourbon.IA",
    description="Assistant législatif 100% local — API du hackathon AN 2026",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://bourbon-ia.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    amendements: list
    model: str = "mac_mistral"
    provider: str = "groq"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    system_prompt: Optional[str] = None
    max_tokens: Optional[int] = None

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
            effective_model = payload.model or "local-model"
            logging.info(f"🔒 SÉCURITÉ : Mode LOCAL activé. Les requêtes partent vers {effective_base_url}. La clé Groq de Vercel est TOTALEMENT IGNORÉE.")
        else:
            effective_base_url = "https://api.groq.com/openai/v1"
            effective_api_key = payload.api_key or os.getenv("GROQ_API_KEY")
            effective_model = payload.model or "llama-3.3-70b-versatile"
            logging.info("☁️ SÉCURITÉ : Mode CLOUD activé. Utilisation de l'API Groq.")
            if not effective_api_key:
                logging.warning("Clé GROQ_API_KEY manquante.")
            
        client = AsyncOpenAI(
            base_url=effective_base_url, 
            api_key=effective_api_key or "DUMMY_KEY", 
            timeout=300.0
        )
        
        system_prompt = payload.system_prompt or (
            "TU DOIS RENVOYER UNIQUEMENT UN TABLEAU JSON BRUT. AUCUN FORMATAGE MARKDOWN. AUCUNE BALISE.\n"
            "RÈGLE ABSOLUE : N'utilise JAMAIS les statuts 'Identique' ou 'Doublon'. Ces statuts sont gérés en amont par le système. Tu dois uniquement détecter les 'Discussion commune' ou 'Isolé'.\n\n"
            "TU ES UN AUTOMATE. Renvoie UNIQUEMENT un tableau JSON pur respectant EXACTEMENT ce format :\n"
            "[{\"id\": \"id_de_lamendement\", \"statut\": \"Discussion commune\" | \"Isolé\", \"justification\": \"...\", \"alerte_couleur\": \"vert\" | \"orange\" | \"gris\"}]\n\n"
            "RÈGLES DE FORMATAGE ABSOLUES ET INTRANSIGEANTES :\n"
            "1. Tu dois renvoyer un tableau JSON valide contenant EXACTEMENT un objet pour chaque amendement fourni.\n"
            "2. Tu DOIS conserver la valeur exacte de la clé 'id' de l'amendement (qui est une chaîne de caractères, ex: 'amdt-185', 'amdt-7rect', 'CD12'). Ne la remplace JAMAIS par un entier.\n"
            "3. La clé 'statut' ne peut avoir QUE l'une de ces 2 valeurs exactes : 'Discussion commune', ou 'Isolé'. Aucune autre valeur n'est tolérée.\n"
            "4. Ne rajoute aucune autre clé. Ne mets pas de texte avant ou après le tableau JSON."
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
                
                models_to_try = [effective_model]
                for m in FALLBACK_MODELS:
                    if m not in models_to_try:
                        models_to_try.append(m)

                last_error = None
                for idx, model_name in enumerate(models_to_try):
                    try:
                        response = await client.chat.completions.create(
                            model=model_name,
                            messages=[{"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}],
                            temperature=0.1
                        )
                        contenu = response.choices[0].message.content.strip()
                        logging.info(f"🚀 PROMPT GROQ:\n{system_prompt}\n\n{user_prompt}")
                        logging.info(f"✅ REPONSE BRUTE GROQ:\n{contenu}")
                        import re
                        raw_text = contenu.strip()
                        
                        # Nettoyage des balises <think> (modèles de raisonnement)
                        raw_text = re.sub(r'<think>[\s\S]*?</think>', '', raw_text, flags=re.IGNORECASE)
                        
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
                        
                        if idx > 0:
                            data_json["justification"] = "⚠️ Changement automatique de modèle suite à une saturation du serveur principal. " + data_json.get("justification", "")

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
                        if "429" in error_str or "rate limit" in error_str or "quota" in error_str or "503" in error_str or "overloaded" in error_str:
                            logging.warning(f"⚠️ Modèle {model_name} épuisé (429/503/Quota) sur l'amendement {amend_id}, passage au suivant...")
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


# ══════════════════════════════════════════════════════════════════════════
# ROUTE V2 — Pipeline End-to-End (Déterministe → Cache → LLM → Data Mapper)
# ══════════════════════════════════════════════════════════════════════════

class V2AnalyzeRequest(BaseModel):
    """Payload d'entrée pour le pipeline V2."""
    amendements: list
    model: str = "local-model"
    base_url: str = "http://localhost:1234/v1"
    api_key: str = "local-key"
    temperature: float = 0.1
    max_tokens: int = 1024


def _build_enriched(raw: dict, index: int) -> EnrichedAmendment:
    """
    Convertit un amendement brut (format AN / normalisé) en EnrichedAmendment Pydantic.
    Tolère les données manquantes grâce aux valeurs par défaut du schéma.
    """
    am = raw.get("amendement", raw)

    # ── Identifiants ──
    uid = am.get("uid") or am.get("id") or f"amdt-{index}"
    numero = str(am.get("identification", {}).get("numeroLong", "") or am.get("numero", ""))

    # ── Texte juridique ──
    corps = am.get("corps", {})
    dispositif_raw = (
        corps.get("contenuAuteur", {}).get("dispositif", "")
        or corps.get("cartoucheInformatif", "")
        or am.get("dispositif", "")
    )
    expose = corps.get("contenuAuteur", {}).get("exposeSommaire", "") or am.get("expose_sommaire", "")

    # ── Division / Article ──
    division = am.get("pointeurFragmentTexte", {}).get("division", {})
    article = division.get("articleDesignationCourte", "") or division.get("titre", "") or am.get("article", "")

    # ── Auteur ──
    signataires = am.get("signataires", {})
    auteur_block = signataires.get("auteur", {}) if isinstance(signataires, dict) else {}
    auteur_ref = auteur_block.get("acteurRef", "") if isinstance(auteur_block, dict) else ""
    groupe_ref = auteur_block.get("groupePolitiqueRef", "") if isinstance(auteur_block, dict) else ""

    # ── Identiques officiels ──
    est_identique = bool(am.get("discussionIdentique") or am.get("estIdentique") or am.get("est_identique_officiel"))
    id_discussion = am.get("idDiscussionIdentique") or am.get("id_discussion_identique")

    return EnrichedAmendment(
        amendement_uid=str(uid),
        numero_long=numero,
        dispositif_raw=str(dispositif_raw) if dispositif_raw else "",
        expose_sommaire=str(expose) if expose else "",
        article_vise=str(article) if article else "",
        auteur_ref=str(auteur_ref),
        auteur_nom=am.get("auteur_nom", "") or "",
        auteur_prenom=am.get("auteur_prenom", "") or "",
        auteur_trigramme=am.get("auteur_trigramme", "") or "",
        groupe_politique_ref=str(groupe_ref),
        groupe_politique=am.get("groupe_politique", "") or "",
        dossier_ref=am.get("texteLegislatifRef", "") or am.get("dossier_ref", "") or "",
        dossier_titre=am.get("dossier_titre", "") or "",
        est_identique_officiel=est_identique,
        id_discussion_identique=str(id_discussion) if id_discussion else None,
    )


def _to_frontend(amend: EnrichedAmendment, llm_result: Optional[dict] = None) -> dict:
    """
    Data Mapper : convertit l'objet Pydantic snake_case en dict camelCase
    consommable directement par les composants React.
    """
    base = {
        # ── Identifiants (utilisés par AmendmentTable) ──
        "uid": amend.amendement_uid,
        "id": amend.amendement_uid,
        "numero": amend.numero_long,
        "article": amend.article_vise,

        # ── Auteur (pour <AuthorBadge>) ──
        "auteur_nom": amend.auteur_nom,
        "auteur_prenom": amend.auteur_prenom,
        "auteur_trigramme": amend.auteur_trigramme,
        "auteurs": [" ".join(p for p in [amend.auteur_prenom, amend.auteur_nom] if p)] if amend.auteur_nom else [amend.auteur_ref or "—"],
        "auteur": " ".join(p for p in [amend.auteur_prenom, amend.auteur_nom] if p) or amend.auteur_ref or "—",

        # ── Groupe politique (pour <PoliticalGroupTag>) ──
        "groupRef": amend.groupe_politique_ref,
        "groupe_politique": amend.groupe_politique,

        # ── Dossier législatif (pour <LegislativeContext>) ──
        "dossier_ref": amend.dossier_ref,
        "title": amend.dossier_titre,

        # ── Identiques officiels (pour <IdentiqueAlert>) ──
        "isIdentical": amend.est_identique_officiel,
        "discussionId": amend.id_discussion_identique,

        # ── Texte juridique ──
        "dispositif": amend.dispositif_raw,
        "dispositif_clean": amend.dispositif_clean,
        "expose_sommaire": amend.expose_sommaire,

        # ── Classification mécanique ──
        "point_impact": {"type": amend.point_impact or ""},
        "statut_mecanique": amend.statut_mecanique,
        "justification_mecanique": amend.justification_mecanique,
        "groupe_identique_id": amend.groupe_identique_id,
    }

    # ── Résultat LLM sémantique (si disponible) ──
    if llm_result:
        statut_llm = llm_result.get("statut", "NOUVEAU")
        couleur = "orange" if statut_llm == "DISCUSSION_COMMUNE" else "vert"
        base["resultat_ia"] = {
            "id": amend.amendement_uid,
            "statut": statut_llm,
            "analyse_intention": llm_result.get("analyse_intention", ""),
            "analyse_politique": llm_result.get("analyse_politique", ""),
            "id_discussion_cible": llm_result.get("id_discussion_cible"),
            "niveau_confiance": llm_result.get("niveau_confiance", 0.0),
            "justification": llm_result.get("analyse_intention", ""),
            "alerte_couleur": couleur,
            "cached": llm_result.get("cached", False),
        }

    # ── Résultat déterministe injecté comme resultat_ia si pas de LLM ──
    if not base.get("resultat_ia") and amend.statut_mecanique != StatutMecanique.NOUVEAU:
        statut_display = {
            StatutMecanique.IDENTIQUE_MECANIQUE: "Identique",
            StatutMecanique.DOUBLON_MECANIQUE: "Doublon",
            StatutMecanique.IDENTIQUE_OFFICIEL: "Identique",
        }.get(amend.statut_mecanique, amend.statut_mecanique)
        couleur = "rouge" if "DOUBLON" in str(amend.statut_mecanique) else "orange"
        base["resultat_ia"] = {
            "id": amend.amendement_uid,
            "statut": statut_display,
            "justification": amend.justification_mecanique,
            "alerte_couleur": couleur,
            "analyse_intention": f"Détecté mécaniquement : {amend.justification_mecanique}",
            "analyse_politique": "Classification déterministe (100 % fiable, sans IA).",
            "niveau_confiance": 1.0,
        }

    return base


@app.post("/api/v2/analyser")
async def v2_analyser(raw_request: Request, payload: V2AnalyzeRequest):
    """
    Pipeline V2 complet : Normalisation → Tri déterministe → Cache → LLM → Data Mapper.
    Retourne une liste de dicts camelCase prêts pour le front-end React.
    """
    start = time.time()
    logging.info(f"🚀 V2 Pipeline démarré pour {len(payload.amendements)} amendement(s)")

    try:
        # ── Phase 1 : Conversion en EnrichedAmendment ──
        enriched: list[EnrichedAmendment] = []
        for i, raw in enumerate(payload.amendements):
            try:
                enriched.append(_build_enriched(raw, i))
            except Exception as exc:
                logging.warning(f"⚠️ Amendement {i} ignoré (conversion) : {exc}")

        if not enriched:
            return []

        # ── Phase 2 : Tri déterministe (Identiques, Doublons, Hiérarchie AN) ──
        enriched = process_deterministic_sorting(enriched)

        # ── Phase 3 : Filtre sémantique LLM (uniquement sur les NOUVEAUX) ──
        resultats_finaux = []
        nouveaux_count = sum(1 for a in enriched if a.statut_mecanique == StatutMecanique.NOUVEAU)
        processed_llm = 0

        for rang, amend in enumerate(enriched, start=1):
            # Vérifier si le client a annulé
            if await raw_request.is_disconnected():
                logging.info("🛑 Client déconnecté, arrêt du pipeline.")
                break

            llm_data = None

            if amend.statut_mecanique == StatutMecanique.NOUVEAU:
                processed_llm += 1

                # ── 3a. Vérifier le cache SQLite ──
                cached = get_cached_classification(amend.amendement_uid)
                if cached:
                    cached["cached"] = True
                    llm_data = cached
                    logging.info(f"📦 Cache HIT {amend.amendement_uid} ({processed_llm}/{nouveaux_count})")
                else:
                    # ── 3b. Appel LLM via asyncio.to_thread (non-bloquant) ──
                    logging.info(f"🧠 LLM START {amend.amendement_uid} ({processed_llm}/{nouveaux_count})")

                    # Construire le dict enrichi pour le moteur sémantique
                    amend_dict = {
                        "amendement": {
                            "uid": amend.amendement_uid,
                            "numeroLong": amend.numero_long,
                            "dispositif": amend.dispositif_raw,
                            "exposeSommaire": amend.expose_sommaire,
                            "divisionArticleDesignation": amend.article_vise,
                        },
                        "auteur": {
                            "nom": amend.auteur_nom,
                            "prenom": amend.auteur_prenom,
                            "trigramme": amend.auteur_trigramme,
                            "groupePolitiqueRef": {"libelle": amend.groupe_politique},
                        },
                        "dossier": {
                            "titre": amend.dossier_titre,
                        },
                    }

                    # Discussions candidates = les autres NOUVEAUX du même article
                    candidats = [
                        {
                            "id_discussion": a.amendement_uid,
                            "amendement": {
                                "divisionArticleDesignation": a.article_vise,
                                "dispositif": a.dispositif_raw,
                            },
                            "auteur": {"groupePolitiqueRef": {"libelle": a.groupe_politique}},
                        }
                        for a in enriched
                        if a.amendement_uid != amend.amendement_uid
                        and a.article_vise == amend.article_vise
                        and a.statut_mecanique == StatutMecanique.NOUVEAU
                    ]

                    try:
                        # evaluate_similitude utilise le client openai synchrone
                        # → asyncio.to_thread évite de bloquer l'event loop FastAPI
                        resultat = await asyncio.to_thread(
                            evaluate_similitude,
                            amend_dict,
                            candidats,
                            payload.base_url,
                            model=payload.model,
                            api_key=payload.api_key,
                            timeout=120.0,
                            max_tokens=payload.max_tokens,
                            temperature=payload.temperature,
                        )
                        llm_data = resultat.model_dump()

                        # ── Sauvegarder en cache ──
                        save_classification(amend.amendement_uid, llm_data)

                    except Exception as exc:
                        logging.error(f"❌ LLM FAIL {amend.amendement_uid} : {exc}")
                        llm_data = {
                            "statut": "NOUVEAU",
                            "analyse_intention": f"Erreur LLM : {str(exc)[:120]}",
                            "analyse_politique": "Analyse sémantique indisponible.",
                            "id_discussion_cible": None,
                            "niveau_confiance": 0.0,
                        }

            # ── Data Mapper : snake_case → camelCase ──
            mapped = _to_frontend(amend, llm_data)
            mapped["rang"] = rang
            if mapped.get("resultat_ia"):
                mapped["resultat_ia"]["rang"] = rang
            resultats_finaux.append(mapped)

        elapsed = time.time() - start
        logging.info(f"✅ V2 Pipeline terminé en {elapsed:.1f}s — {len(resultats_finaux)} résultat(s)")
        return resultats_finaux

    except Exception as exc:
        logging.error(f"❌ V2 Pipeline CRASH : {exc}", exc_info=True)
        # Fallback de survie
        return [
            {
                "id": raw.get("amendement", raw).get("uid", f"err-{i}"),
                "numero": "Erreur",
                "article": "",
                "auteurs": [],
                "resultat_ia": {
                    "id": f"err-{i}",
                    "statut": "Erreur",
                    "justification": f"Erreur pipeline V2 : {str(exc)[:200]}",
                    "alerte_couleur": "rouge",
                },
            }
            for i, raw in enumerate(payload.amendements)
        ]


class AnalyzeBatchRequest(BaseModel):
    user_prompt: str
    system_prompt: str
    model: str = "mac_mistral"
    provider: str = "groq"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: Optional[int] = None

@app.post("/api/analyze_batch")
async def analyze_batch_endpoint(payload: AnalyzeBatchRequest):
    try:
        from openai import AsyncOpenAI
        if payload.provider == "local":
            effective_base_url = payload.base_url or "http://localhost:1234/v1"
            effective_api_key = payload.api_key or "local-key"
            effective_model = payload.model or "local-model"
        else:
            effective_base_url = "https://api.groq.com/openai/v1"
            effective_api_key = payload.api_key or os.getenv("GROQ_API_KEY")
            effective_model = payload.model or "llama-3.3-70b-versatile"
            
        client = AsyncOpenAI(
            base_url=effective_base_url, 
            api_key=effective_api_key or "DUMMY_KEY", 
            timeout=300.0
        )
        
        response = await client.chat.completions.create(
            model=effective_model,
            messages=[{"role": "user", "content": f"{payload.system_prompt}\n\n{payload.user_prompt}"}],
            temperature=0.1
        )
        contenu = response.choices[0].message.content.strip()
        import re
        raw_text = contenu.strip()
        raw_text = re.sub(r'<think>[\s\S]*?</think>', '', raw_text, flags=re.IGNORECASE)
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text)
        contenu = raw_text.strip()
        json_match = re.search(r'\[.*\]|\{.*\}', contenu, re.DOTALL)
        if json_match:
            contenu = json_match.group(0)
            
        return json.loads(contenu)
    except Exception as e:
        import traceback
        logging.error(f"Erreur analyze_batch: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
