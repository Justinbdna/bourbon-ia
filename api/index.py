import json
import logging
import os
import re
import time
import asyncio
import html
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
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
    from api.deputes_resolver import resolve_signataires
    from api.textes_resolver import extract_texte_ref, get_textes_reference, match_article_reference
except ModuleNotFoundError:
    from deterministic_engine import process_deterministic_sorting, normalize_text
    from schemas import EnrichedAmendment, StatutMecanique
    from llm_semantic_engine import evaluate_similitude
    from cache_manager import get_cached_classification, save_classification
    try:
        from deputes_resolver import resolve_signataires
    except Exception:
        def resolve_signataires(x):
            return {"auteurs_formatte": str(x) if x else "", "groupe_principal": "", "est_rapporteur": False}
    try:
        from textes_resolver import extract_texte_ref, get_textes_reference, match_article_reference
    except Exception:
        def extract_texte_ref(x): return ""
        def get_textes_reference(x): return {}
        def match_article_reference(d, a): return None

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

            # Résolution enrichie facultative sécurisée
            try:
                res_sig = resolve_signataires(signataires or auteur)
                if res_sig.get("auteurs_formatte"):
                    auteur = res_sig["auteurs_formatte"]
            except Exception as e:
                logging.debug(f"Résolution signataire ignorée pour amendement {index}: {e}")

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
@app.post("/api/v2/normaliser")
async def normalize_endpoint(payload: AnalyzeRequest):
    try:
        # Résolution automatique du dossier législatif de référence
        texte_ref_id = extract_texte_ref(payload.amendements)
        textes_dict = get_textes_reference(texte_ref_id) if texte_ref_id else {}

        results = []
        for i, a in enumerate(payload.amendements):
            try:
                norm = normaliser_amendement(a, i)
                if textes_dict and norm.get("article"):
                    norm["texte_loi_reference"] = match_article_reference(textes_dict, norm["article"])
                results.append(norm)
            except Exception as exc:
                logging.warning(f"⚠️ Erreur normalisation amendement {i}: {exc}")
                results.append({"id": f"amdt-err-{i}", "numero": "Erreur", "article": "", "auteurs": [], "point_impact": {"type": ""}, "dispositif": "", "texte": "", "auteur": ""})
        return results
    except Exception as e:
        import traceback
        logging.error(f"❌ Crash normalize_endpoint: {e}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Erreur de normalisation: {str(e)}"}
        )

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
    llm_endpoint: Optional[str] = None
    base_url: str = "http://localhost:1234/v1" # rétrocompatibilité V1
    api_key: str = "local-key"
    temperature: float = 0.1
    max_tokens: int = 1024
    textes_reference: dict[str, str] = Field(default_factory=dict, description="Texte de loi initial par article (ex: {'Article 1er': '...'})")

class V2AnalyzeSingleRequest(V2AnalyzeRequest):
    """Payload d'entrée pour l'analyse d'un seul amendement (avec contexte global)."""
    target_uid: str


def _inject_textes_reference(enriched_list: list[EnrichedAmendment], textes_ref: dict[str, str]):
    """Injecte le texte initial du projet de loi correspondant à l'article visé."""
    if not textes_ref:
        return
    for a in enriched_list:
        if a.article_vise and not a.texte_loi_reference:
            matched = match_article_reference(textes_ref, a.article_vise)
            if matched:
                a.texte_loi_reference = matched


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

    # ── Détection de qualité Rapporteur / Commission ──
    qualite_auteur = str(auteur_block.get("qualite") or "").lower()
    is_rapporteur = "rapporteur" in qualite_auteur or "commission" in qualite_auteur
    if not is_rapporteur and am.get("auteurs"):
        auteurs_join = " ".join(str(x) for x in am.get("auteurs", [])).lower()
        if "rapporteur" in auteurs_join or "commission" in auteurs_join:
            is_rapporteur = True

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
        auteurs_raw=am.get("auteurs", []),
        groupe_politique_ref=str(groupe_ref),
        groupe_politique=am.get("groupe_politique", "") or "",
        dossier_ref=am.get("texteLegislatifRef", "") or am.get("dossier_ref", "") or "",
        dossier_titre=am.get("dossier_titre", "") or "",
        est_identique_officiel=est_identique,
        id_discussion_identique=str(id_discussion) if id_discussion else None,
        est_rapporteur=is_rapporteur,
        raw_dict=raw,
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
        "auteur": {
            "nom": amend.auteur_nom,
            "prenom": amend.auteur_prenom,
            "trigramme": amend.auteur_trigramme,
        },
        "auteur_string": " ".join(p for p in [amend.auteur_prenom, amend.auteur_nom] if p) or (amend.auteurs_raw[0] if amend.auteurs_raw else (amend.auteur_ref or "—")),
        "auteurs": amend.auteurs_raw if amend.auteurs_raw else ([" ".join(p for p in [amend.auteur_prenom, amend.auteur_nom] if p)] if amend.auteur_nom else [amend.auteur_ref or "—"]),
        "auteurs_raw": amend.auteurs_raw,

        # ── Groupe politique (pour <PoliticalGroupTag>) ──
        "groupRef": amend.groupe_politique_ref,
        "groupe_politique": amend.groupe_politique,
        "groupe": amend.groupe_politique,
        "est_rapporteur": amend.est_rapporteur,
        "texte_loi_reference": amend.texte_loi_reference,

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
        if statut_llm == "NOUVEAU":
            statut_llm = "Isolé"
            
        if statut_llm == "Discussion commune":
            couleur = "orange"
        elif statut_llm == "Similaire":
            couleur = "vert"
        else:
            couleur = "gris" # Isolé
            
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
        if amend.statut_mecanique == StatutMecanique.ISOLE_MECANIQUE:
            statut_display = "Isolé"
            couleur = "gris"
            intention = f"Détecté mécaniquement : {amend.justification_mecanique}"
            politique = "Amendement sans concurrence sur sa zone d'impact (isolé d'office sans LLM)."
            confiance = 1.0
        else:
            statut_display = "Identique" # Strict mapping anti-jargon
            couleur = "rouge" if "DOUBLON" in str(amend.statut_mecanique) else "orange"
            intention = f"Détecté mécaniquement : {amend.justification_mecanique}"
            politique = "Classification déterministe (100 % fiable, sans IA)."
            confiance = 1.0

        base["resultat_ia"] = {
            "id": amend.amendement_uid,
            "statut": statut_display,
            "justification": amend.justification_mecanique,
            "alerte_couleur": couleur,
            "analyse_intention": intention,
            "analyse_politique": politique,
            "niveau_confiance": confiance,
        }
    elif not base.get("resultat_ia") and amend.statut_mecanique == StatutMecanique.NOUVEAU:
        base["resultat_ia"] = {
            "id": amend.amendement_uid,
            "statut": "Isolé",
            "justification": "En attente d'analyse IA...",
            "alerte_couleur": "gris",
            "analyse_intention": "",
            "analyse_politique": "",
            "niveau_confiance": 0.0,
        }

    # ── Drapeaux de clustering et d'optimisation LLM ──
    base["_skipLLM"] = bool(amend.skip_llm or amend.statut_mecanique != StatutMecanique.NOUVEAU)
    base["skip_llm"] = base["_skipLLM"]
    base["cluster_id"] = amend.cluster_id

    # ── Whitelist et filtrage de sécurité (C-03) ──
    # Ne préserver que les clés inoffensives provenant des données d'origine
    WHITELIST_RAW_KEYS = {
        "rapporteur", "sort", "dateDepot", "dateSort", "statut", "signataires", "coSignataires",
        "texte", "numOrdre", "dossierRef", "triAmendement"
    }

    filtered_raw = {}
    if amend.raw_dict and isinstance(amend.raw_dict, dict):
        for k, v in amend.raw_dict.items():
            if not k.startswith("_") and (k in WHITELIST_RAW_KEYS or k in base):
                filtered_raw[k] = v

    filtered_raw.update(base)

    # Filtrage strict de sécurité : élimination absolue de toute clé privée/technique commençant par '_' (sauf _skipLLM requis pour l'orchestrateur frontend)
    return {k: v for k, v in filtered_raw.items() if not k.startswith("_") or k == "_skipLLM"}

@app.post("/api/v2/mecanique")
async def v2_mecanique(payload: V2AnalyzeRequest):
    """
    Route ultra-rapide (sans LLM) pour renvoyer le tri mécanique immédiatement.
    """
    try:
        # Auto-résolution du dossier législatif si non fourni
        textes_ref = payload.textes_reference
        if not textes_ref:
            texte_ref_id = extract_texte_ref(payload.amendements)
            if texte_ref_id:
                textes_ref = get_textes_reference(texte_ref_id)

        enriched = []
        for i, raw in enumerate(payload.amendements):
            try:
                enriched.append(_build_enriched(raw, i))
            except Exception as exc:
                logging.warning(f"⚠️ Amendement {i} ignoré (conversion) : {exc}")

        if not enriched:
            return []

        if textes_ref:
            try:
                _inject_textes_reference(enriched, textes_ref)
            except Exception as exc:
                logging.warning(f"⚠️ Erreur injection textes_reference : {exc}")

        try:
            enriched = process_deterministic_sorting(enriched)
        except Exception as exc:
            logging.error(f"❌ Erreur process_deterministic_sorting : {exc}")
            for a in enriched:
                a.statut_mecanique = StatutMecanique.ISOLE_MECANIQUE
                a.justification_mecanique = "Repli : tri mécanique non appliqué suite à une anomalie."

        return [_to_frontend(a) for a in enriched]
    except Exception as e:
        import traceback
        logging.error(f"❌ Crash v2_mecanique: {e}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Erreur interne lors du tri mécanique: {str(e)}", "details": str(e)}
        )


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

        # ── Injection des textes de référence de loi (avec auto-résolution) ──
        textes_ref = payload.textes_reference
        if not textes_ref:
            texte_ref_id = extract_texte_ref(payload.amendements)
            if texte_ref_id:
                textes_ref = get_textes_reference(texte_ref_id)

        if textes_ref:
            _inject_textes_reference(enriched, textes_ref)

        # ── Phase 2 : Tri déterministe (Identiques, Doublons, Hiérarchie AN) ──
        enriched = process_deterministic_sorting(enriched)

        # ── Phase 3 : Filtre sémantique LLM (uniquement sur les NOUVEAUX) ──
        nouveaux_count = sum(1 for a in enriched if a.statut_mecanique == StatutMecanique.NOUVEAU)
        processed_llm = [0] # Liste pour mutabilité dans process_llm
        
        # Sémaphore pour limiter le nombre de requêtes simultanées
        semaphore = asyncio.Semaphore(2)
        
        async def process_llm(amend: EnrichedAmendment, rang: int) -> dict:
            llm_data = None
            if amend.statut_mecanique == StatutMecanique.NOUVEAU:
                processed_llm[0] += 1
                cached = get_cached_classification(amend.amendement_uid)
                if cached:
                    cached["cached"] = True
                    llm_data = cached
                    logging.info(f"📦 Cache HIT {amend.amendement_uid} ({processed_llm[0]}/{nouveaux_count})")
                else:
                    logging.info(f"🧠 LLM START {amend.amendement_uid} ({processed_llm[0]}/{nouveaux_count})")
                    contexte_rag = ""
                    try:
                        from api.tricoteuses_client import fetch_amendements
                        def fetch_rag():
                            res = fetch_amendements(uid=amend.amendement_uid, timeout=1.9)
                            if not res: return ""
                            
                            auteur_dict = res.get("auteur", {}) or {}
                            nom = auteur_dict.get("nom", "")
                            prenom = auteur_dict.get("prenom", "")
                            groupe = (auteur_dict.get("groupePolitiqueRef") or {}).get("libelle", "Inconnu")
                            nom_auteur = f"{prenom} {nom}".strip() or "Inconnu"
                            
                            dossier = res.get("dossierRef", {}) or {}
                            statut_texte = dossier.get("titre", "Non renseigné")
                            
                            cosign = res.get("coSignataires", []) or []
                            signataires = ", ".join([f"{s.get('prenom', '')} {s.get('nom', '')}".strip() for s in cosign]) if cosign else "Aucun"
                            
                            return (
                                f"\n## CONTEXTE POLITIQUE (RAG API)\n"
                                f"- Auteur : {nom_auteur} ({groupe})\n"
                                f"- Co-signataires : {signataires}\n"
                                f"- Statut du texte : {statut_texte}\n"
                            )
                        
                        contexte_rag = await asyncio.to_thread(fetch_rag)
                    except Exception as e:
                        logging.warning(f"RAG echoué pour {amend.amendement_uid}: {e}")

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
                        "dossier": {"titre": amend.dossier_titre},
                        "contexte_rag": contexte_rag,
                        "texte_loi_reference": amend.texte_loi_reference,
                    }
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
                    
                    async with semaphore:
                        try:
                            resultat = await asyncio.to_thread(
                                evaluate_similitude,
                                amend_dict, candidats,
                                llm_endpoint=payload.llm_endpoint or payload.base_url,
                                model=payload.model, api_key=payload.api_key,
                                timeout=120.0, max_tokens=payload.max_tokens, temperature=payload.temperature,
                                texte_loi_reference=amend.texte_loi_reference,
                            )
                            llm_data = resultat.model_dump()
                            save_classification(amend.amendement_uid, llm_data)
                        except Exception as exc:
                            logging.error(f"❌ LLM FAIL {amend.amendement_uid} : {exc}")
                            llm_data = {
                                "statut": "Erreur IA",
                                "analyse_intention": "⚠️ Impossible de joindre l'IA (Serveur local ou tunnel Ngrok hors-ligne). Vérifiez vos réglages IA.",
                                "analyse_politique": "Analyse sémantique indisponible.",
                                "id_discussion_cible": None,
                                "niveau_confiance": 0.0,
                                "alerte_couleur": "rouge",
                            }
            
            mapped = _to_frontend(amend, llm_data)
            mapped["rang"] = rang
            if mapped.get("resultat_ia"):
                mapped["resultat_ia"]["rang"] = rang
            return mapped

        # Exécution parallèle de tous les LLM
        tasks = [process_llm(amend, rang) for rang, amend in enumerate(enriched, start=1)]
        resultats_finaux = await asyncio.gather(*tasks)

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


@app.post("/api/v2/analyser-llm")
async def v2_analyser_llm(payload: V2AnalyzeSingleRequest):
    """
    Route unitaire : analyse un seul amendement (statut NOUVEAU) via RAG + LLM.
    """
    try:
        # Auto-résolution du dossier législatif si non fourni
        textes_ref = payload.textes_reference
        if not textes_ref:
            texte_ref_id = extract_texte_ref(payload.amendements)
            if texte_ref_id:
                textes_ref = get_textes_reference(texte_ref_id)

        enriched: list[EnrichedAmendment] = []
        for i, raw in enumerate(payload.amendements):
            try:
                enriched.append(_build_enriched(raw, i))
            except Exception:
                pass
        
        if textes_ref:
            _inject_textes_reference(enriched, textes_ref)

        enriched = process_deterministic_sorting(enriched)
        
        target = next((a for a in enriched if a.amendement_uid == payload.target_uid), None)
        if not target:
            return {"error": "Target amendment not found"}

        if not target.texte_loi_reference and textes_ref and target.article_vise:
            target.texte_loi_reference = match_article_reference(textes_ref, target.article_vise)
            
        target_rang = next((i for i, a in enumerate(enriched, start=1) if a.amendement_uid == payload.target_uid), 1)

        llm_data = None
        if target.statut_mecanique == StatutMecanique.NOUVEAU:
            cached = get_cached_classification(target.amendement_uid)
            if cached:
                cached["cached"] = True
                llm_data = cached
            else:
                contexte_rag = ""
                try:
                    from api.tricoteuses_client import fetch_amendements, fetch_acteurs
                    def fetch_rag():
                        res = fetch_amendements(uid=target.amendement_uid, timeout=1.9)
                        if not res: return "", "Inconnu", "", "Inconnu"
                        
                        amend_data = res.get("data", {})
                        acteur_ref = amend_data.get("signataires", {}).get("auteur", {}).get("acteurRef")
                        
                        nom_auteur = "Inconnu"
                        prenom_auteur = ""
                        groupe = "Inconnu"
                        
                        if acteur_ref:
                            try:
                                acteur_res = fetch_acteurs(uid=acteur_ref, timeout=1.5)
                                if acteur_res:
                                    acteur_data = acteur_res.get("data", {})
                                    ident = acteur_data.get("etatCivil", {}).get("ident", {})
                                    nom_auteur = ident.get("nom", "Inconnu")
                                    prenom_auteur = ident.get("prenom", "")
                                    groupe = (acteur_data.get("groupePolitiqueRef") or acteur_data.get("groupe") or {}).get("libelle", "Inconnu")
                            except Exception as e:
                                logging.warning(f"RAG fetch_acteurs echoué pour {acteur_ref}: {e}")
                        
                        nom_complet = f"{prenom_auteur} {nom_auteur}".strip() or "Inconnu"
                        dossier = amend_data.get("dossierRef", {}) or {}
                        statut_texte = dossier.get("titre", "Non renseigné")
                        cosign = amend_data.get("signataires", {}).get("cosignataires", []) or []
                        signataires = f"{len(cosign)} cosignataires" if cosign else "Aucun"
                        
                        contexte = (
                            f"\n## CONTEXTE POLITIQUE (RAG API)\n"
                            f"- Auteur : {nom_complet} ({groupe})\n"
                            f"- Co-signataires : {signataires}\n"
                            f"- Statut du texte : {statut_texte}\n"
                        )
                        return contexte, nom_auteur, prenom_auteur, groupe
                        
                    contexte_rag, req_nom, req_prenom, req_groupe = await asyncio.to_thread(fetch_rag)
                    if req_nom != "Inconnu":
                        target.auteur_nom = req_nom
                        target.auteur_prenom = req_prenom
                        target.groupe_politique = req_groupe
                except Exception as e:
                    logging.warning(f"RAG global echoué pour {target.amendement_uid}: {e}")

                amend_dict = {
                    "amendement": {
                        "uid": target.amendement_uid,
                        "numeroLong": target.numero_long,
                        "dispositif": target.dispositif_raw,
                        "exposeSommaire": target.expose_sommaire,
                        "divisionArticleDesignation": target.article_vise,
                    },
                    "auteur": {
                        "nom": target.auteur_nom,
                        "prenom": target.auteur_prenom,
                        "trigramme": target.auteur_trigramme,
                        "groupePolitiqueRef": {"libelle": target.groupe_politique},
                    },
                    "dossier": {"titre": target.dossier_titre},
                    "contexte_rag": contexte_rag,
                    "texte_loi_reference": target.texte_loi_reference,
                }
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
                    if a.amendement_uid != target.amendement_uid
                    and a.article_vise == target.article_vise
                    and a.statut_mecanique == StatutMecanique.NOUVEAU
                ]
                
                try:
                    resultat = await asyncio.to_thread(
                        evaluate_similitude,
                        amend_dict, candidats,
                        llm_endpoint=payload.llm_endpoint or payload.base_url,
                        model=payload.model, api_key=payload.api_key,
                        timeout=120.0, max_tokens=payload.max_tokens, temperature=payload.temperature,
                        texte_loi_reference=target.texte_loi_reference,
                    )
                    llm_data = resultat.model_dump()
                    save_classification(target.amendement_uid, llm_data)
                except Exception as exc:
                    logging.error(f"❌ LLM FAIL {target.amendement_uid} : {exc}")
                    exc_str = str(exc)
                    exc_name = type(exc).__name__
                    if "AuthenticationError" in exc_name or "401" in exc_str or "Invalid API Key" in exc_str or "invalid_api_key" in exc_str:
                        error_msg = "⚠️ Clé API invalide ou expirée. Veuillez vérifier et mettre à jour votre clé dans les Réglages IA."
                    else:
                        error_msg = "⚠️ Impossible de joindre l'IA (Serveur local ou tunnel Ngrok hors-ligne). Vérifiez vos réglages IA."

                    llm_data = {
                        "statut": "Erreur IA",
                        "analyse_intention": error_msg,
                        "analyse_politique": "Analyse sémantique indisponible.",
                        "id_discussion_cible": None,
                        "niveau_confiance": 0.0,
                        "alerte_couleur": "rouge",
                    }

        mapped = _to_frontend(target, llm_data)
        mapped["rang"] = target_rang
        if mapped.get("resultat_ia"):
            mapped["resultat_ia"]["rang"] = target_rang
        return mapped
        
    except Exception as exc:
        logging.error(f"❌ V2 LLM CRASH : {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur d'analyse LLM : {str(exc)}")
