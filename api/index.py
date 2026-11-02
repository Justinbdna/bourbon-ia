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
from pydantic import BaseModel, Field, ConfigDict
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
    from api.deterministic_engine import (
        process_deterministic_sorting,
        normalize_text,
        strip_html_for_display,
        detect_gage_financier,
        get_article_sort_key,
    )
    from api.schemas import EnrichedAmendment, StatutMecanique, SurtranspositionRequest
    from api.llm_semantic_engine import evaluate_similitude, validate_endpoint_url, sanitize_log_message, resumer_amendement
    from api.cache_manager import get_cached_classification, save_classification
    from api.deputes_resolver import resolve_signataires, MAPPING_ORGANES_XVII, get_depute_info
    from api.textes_resolver import extract_texte_ref, get_textes_reference, match_article_reference
    from api.commissions_resolver import resoudre_commission_et_mots_cles
    from api.participants_resolver import fetch_participants, resumer_par_groupe, resolve_dossier_ref
except ModuleNotFoundError:
    from deterministic_engine import (
        process_deterministic_sorting,
        normalize_text,
        strip_html_for_display,
        detect_gage_financier,
        get_article_sort_key,
    )
    from schemas import EnrichedAmendment, StatutMecanique, SurtranspositionRequest
    from llm_semantic_engine import evaluate_similitude, validate_endpoint_url, sanitize_log_message, resumer_amendement
    from cache_manager import get_cached_classification, save_classification
    try:
        from deputes_resolver import resolve_signataires, MAPPING_ORGANES_XVII, get_depute_info
    except Exception:
        def resolve_signataires(x):
            return {"auteurs_formatte": str(x) if x else "", "groupe_principal": "", "est_rapporteur": False}
        MAPPING_ORGANES_XVII = {}
        def get_depute_info(x): return None
    try:
        from textes_resolver import extract_texte_ref, get_textes_reference, match_article_reference
    except Exception:
        def extract_texte_ref(x): return ""
        def get_textes_reference(x): return {}
        def match_article_reference(d, a): return None
    try:
        from commissions_resolver import resoudre_commission_et_mots_cles
    except Exception:
        def resoudre_commission_et_mots_cles(a):
            return {"commission_ref": "", "commission_libelle": "", "commission_abrege": "",
                    "commission_mots_cles": [], "commission_hors_champ": False}
    try:
        from participants_resolver import fetch_participants, resumer_par_groupe, resolve_dossier_ref
    except Exception:
        def fetch_participants(d, limite=100, utiliser_cache=True): return []
        def resumer_par_groupe(p): return []
        def resolve_dossier_ref(a): return ""


def clean_html_text(text: str) -> str:
    """
    Supprime les balises HTML et décode les entités XML/HTML pour un texte pur et net.
    Exemple : '<p style="text-align: justify;">Supprimer cet article.</p>' -> 'Supprimer cet article.'
    """
    if not text:
        return ""
    decoded = html.unescape(str(text))
    # Préserver les sauts de ligne pour les balises de paragraphe et de saut
    decoded = re.sub(r"<(?:br|/p|/div)[^>]*>", "\n", decoded, flags=re.IGNORECASE)
    clean = re.sub(r"<[^>]+>", "", decoded)
    clean = clean.replace("\xa0", " ").replace("&#160;", " ")
    clean = re.sub(r"[ \t]+", " ", clean)
    clean = re.sub(r"\n\s*\n+", "\n\n", clean)
    return clean.strip()


def extract_dispositif_raw(am: dict) -> str:
    """
    Extrait le dispositif en vérifiant TOUS les chemins possibles de l'Assemblée nationale :
      1. Chemin standard imbriqué : corps.contenuAuteur.dispositif
      2. Chemin à plat : corps.dispositif
      3. Chemin racine : dispositif
      4. Repli cartoucheInformatif si chaîne valide
    """
    if not isinstance(am, dict):
        return ""

    corps = am.get("corps") if isinstance(am.get("corps"), dict) else {}
    contenu_auteur = corps.get("contenuAuteur") if isinstance(corps.get("contenuAuteur"), dict) else {}

    # 1. Imbriqué standard
    disp = contenu_auteur.get("dispositif")
    if disp and isinstance(disp, str) and disp.strip():
        return clean_html_text(disp)

    # 2. À plat sous corps
    disp = corps.get("dispositif")
    if disp and isinstance(disp, str) and disp.strip():
        return clean_html_text(disp)

    # 3. Racine
    disp = am.get("dispositif")
    if disp and isinstance(disp, str) and disp.strip():
        return clean_html_text(disp)

    # 4. Cartouche informatif seulement si c'est du texte
    cartouche = corps.get("cartoucheInformatif")
    if cartouche and isinstance(cartouche, str) and cartouche.strip():
        return clean_html_text(cartouche)

    return ""


def extract_expose_sommaire(am: dict) -> str:
    """
    Extrait l'exposé sommaire en vérifiant TOUS les chemins possibles :
      1. corps.contenuAuteur.exposeSommaire
      2. corps.exposeSommaire
      3. exposeSommaire / expose_sommaire
    """
    if not isinstance(am, dict):
        return ""

    corps = am.get("corps") if isinstance(am.get("corps"), dict) else {}
    contenu_auteur = corps.get("contenuAuteur") if isinstance(corps.get("contenuAuteur"), dict) else {}

    candidates = [
        contenu_auteur.get("exposeSommaire"),
        corps.get("exposeSommaire"),
        am.get("exposeSommaire"),
        am.get("expose_sommaire"),
    ]
    for c in candidates:
        if c and isinstance(c, str) and c.strip():
            return clean_html_text(c)

    return ""


def format_article_title(art_str: str) -> str:
    """
    Formate le titre d'article pour éviter les doublons ('Article Article PREMIER').
    """
    if not art_str:
        return ""
    s = str(art_str).strip()
    s = re.sub(r"^(article\s+|art\.\s*)+", "Article ", s, flags=re.IGNORECASE)
    if re.match(r"^(premier|1er|\d+)\b", s, flags=re.IGNORECASE):
        s = f"Article {s}"
    return s

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
    model_config = ConfigDict(use_enum_values=True)
    amendements: list = Field(..., max_length=2000)
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

def _nettoyer_html(texte: Any) -> str:
    """
    Retire le balisage HTML du texte destiné à l'AFFICHAGE.
    Utilise strip_html_for_display pour supprimer les balises et décoder les entités HTML/XML.
    """
    return strip_html_for_display(texte)


def _enrichir_a_import(resultat: dict, source: dict, signataires=None) -> dict:
    """
    Ajoute groupe politique, commission, détection gage et assainissement DÈS L'IMPORT.
    """
    try:
        # ── Nettoyage HTML pour l'affichage (données AN réelles) ──
        for champ in ("dispositif", "texte", "expose_sommaire", "exposeSommaire"):
            if resultat.get(champ):
                resultat[champ] = strip_html_for_display(resultat[champ])

        # ── Détection de gage financier au titre de l'Art. 40 ──
        resultat["est_gage"] = detect_gage_financier(
            resultat.get("dispositif", "") or source.get("dispositif", ""),
            source,
        )

        # ── Groupe politique (référentiel local des députés) ──
        if not resultat.get("groupe_politique"):
            source_sig = (
                signataires
                or source.get("auteurs")
                or resultat.get("auteurs")
                or resultat.get("auteur")
            )
            if source_sig:
                resolu = resolve_signataires(source_sig)
                groupe = resolu.get("groupe_principal", "") or ""
                if groupe:
                    resultat["groupe_politique"] = groupe
                    resultat["groupe"] = groupe
        elif not resultat.get("groupe"):
            resultat["groupe"] = resultat["groupe_politique"]

        # ── Commission + thèmes corrélés (uid d'organe embarqué dans l'uid) ──
        if not resultat.get("commission"):
            base = dict(source) if isinstance(source, dict) else {}
            base.setdefault("uid", resultat.get("id", ""))
            base.setdefault("dispositif", resultat.get("dispositif", ""))
            base.setdefault("exposeSommaire", resultat.get("expose_sommaire", ""))
            com = resoudre_commission_et_mots_cles(base)
            if com.get("commission_ref"):
                resultat["commission_ref"] = com["commission_ref"]
                resultat["commission"] = com.get("commission_abrege") or com.get("commission_libelle", "")
                resultat["commission_libelle"] = com.get("commission_libelle", "")
                resultat["commission_mots_cles"] = com.get("commission_mots_cles", [])
                resultat["commission_hors_champ"] = com.get("commission_hors_champ", False)
    except Exception as exc:  # noqa: BLE001
        logging.debug(f"Enrichissement à l'import ignoré : {exc}")
    return resultat


def normaliser_amendement(data, index: int = 0) -> dict:
    try:
        if not isinstance(data, dict):
            logging.warning(f"normaliser_amendement: entrée non-dict ignorée (type={type(data).__name__})")
            return {"id": f"amdt-{index}", "numero": "Inconnu", "article": "", "auteurs": [], "point_impact": {"type": ""}, "dispositif": "", "texte": "", "auteur": ""}
        
        # Selon le parsing frontend, l'objet peut être enveloppé par "amendement" ou l'être directement
        am = data.get("amendement", data)
        
        # On vérifie si c'est bien une structure de l'Assemblée (identification ou uid)
        # On vérifie si c'est bien une structure de l'Assemblée (identification ou uid)
        if "identification" in am or "uid" in am or "pointeurFragmentTexte" in am:
            def safe_str(val, default=""):
                if isinstance(val, dict):
                    if "@xmlns" in val or "@xmlns:xsi" in val or "@xsi:nil" in val:
                        return default
                    import json
                    return json.dumps(val, ensure_ascii=False)
                if isinstance(val, list):
                    import json
                    return json.dumps(val, ensure_ascii=False)
                res = str(val) if val is not None and str(val).strip() != "" else default
                return html.unescape(res)

            raw_numero = am.get("identification", {}).get("numeroLong", "Inconnu")
            numero = safe_str(raw_numero, "Inconnu")
            
            div = am.get("pointeurFragmentTexte", {}).get("division", {})
            raw_article = div.get("articleDesignationCourte") or div.get("titre") or ""
            article = format_article_title(safe_str(raw_article))
            
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
            
            dispositif = extract_dispositif_raw(am)
            expose_sommaire = extract_expose_sommaire(am)
                
            raw_uid = am.get("uid", numero)
            uid = safe_str(raw_uid, numero)

            resultat = {
                "id": uid or f"amdt-{index}",
                "numero": numero,
                "article": article,
                "auteurs": [auteur] if auteur else [],
                "point_impact": {"type": impact},
                "dispositif": dispositif,
                "texte": dispositif,
                "expose_sommaire": expose_sommaire,
                "exposeSommaire": expose_sommaire,
                "auteur": auteur
            }
            return _enrichir_a_import(resultat, am, signataires)

        # Données déjà plates (ex: sampleAmendments.json)
        if not data.get("id"):
            data["id"] = f"amdt-{index}"
        if not data.get("dispositif"):
            data["dispositif"] = extract_dispositif_raw(data)
            data["texte"] = data["dispositif"]
        else:
            data["dispositif"] = clean_html_text(data["dispositif"])
            data["texte"] = data["dispositif"]
        if not data.get("expose_sommaire") and not data.get("exposeSommaire"):
            data["expose_sommaire"] = extract_expose_sommaire(data)
        if data.get("article"):
            data["article"] = format_article_title(data["article"])
        return _enrichir_a_import(data, data, data.get("signataires"))
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
        results.sort(key=lambda r: get_article_sort_key(r))
        return results
    except Exception as e:
        import traceback
        logging.error(f"❌ Crash normalize_endpoint: {e}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Erreur de normalisation: {str(e)}"}
        )

@app.get("/api/participants")
def participants_endpoint(
    dossier_ref: Optional[str] = None,
    amendement_uid: Optional[str] = None,
    limite: int = 100,
):
    """
    Participants d'un TEXTE DE LOI : nom de famille, prénom, groupe politique,
    rôle tenu (rapporteur, initiateur, auteur, cosignataire) et implication.

    Granularité volontairement au niveau du DOSSIER et non de l'amendement :
    un texte courant compte 200+ participants, inaffichables ligne par ligne.

    Accepte `dossier_ref` (DLR…) OU `amendement_uid` (AM…) : beaucoup d'imports
    ne portent aucune référence de dossier, le second paramètre permet alors de
    reconstruire le lien en un unique appel.

    Ne renvoie jamais d'erreur : en cas d'indisponibilité réseau, la liste est
    vide et le panneau front s'affiche sans bloquer le dérouleur.
    """
    if not dossier_ref and amendement_uid:
        dossier_ref = resolve_dossier_ref([{"uid": amendement_uid}])

    if not dossier_ref:
        return {"dossier_ref": "", "total": 0, "participants": [], "par_groupe": []}

    participants = fetch_participants(dossier_ref, limite=limite)
    return {
        "dossier_ref": dossier_ref,
        "total": len(participants),
        "participants": participants,
        "par_groupe": resumer_par_groupe(participants),
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ══════════════════════════════════════════════════════════════════════════
# ROUTE V2 — Pipeline End-to-End (Déterministe → Cache → LLM → Data Mapper)
# ══════════════════════════════════════════════════════════════════════════

class V2AnalyzeRequest(BaseModel):
    """Payload d'entrée pour le pipeline V2."""
    model_config = ConfigDict(use_enum_values=True)
    amendements: list = Field(..., max_length=2000)
    model: str = "local-model"
    llm_endpoint: Optional[str] = None
    base_url: str = "http://localhost:1234/v1" # rétrocompatibilité V1
    api_key: str = "local-key"
    provider: str = "local"  # "local" | "groq" (clé utilisateur) | "groq_auto" (clé serveur)
    temperature: float = 0.1
    max_tokens: int = 1024
    textes_reference: dict[str, str] = Field(default_factory=dict, description="Texte de loi initial par article (ex: {'Article 1er': '...'})")

class V2AnalyzeSingleRequest(V2AnalyzeRequest):
    """Payload d'entrée pour l'analyse d'un seul amendement (avec contexte global)."""
    target_uid: str


class ResumeRequest(BaseModel):
    """Payload de /api/v2/resumer : un amendement + les réglages IA (mêmes champs que V2)."""
    amendement_uid: Optional[str] = Field(None, max_length=150)
    article: Optional[str] = Field(None, max_length=200)
    dispositif: str = Field("", max_length=500_000)
    expose_sommaire: Optional[str] = Field("", max_length=500_000)
    texte_loi_reference: Optional[str] = Field(None, max_length=500_000)
    model: str = Field("local-model", max_length=200)
    llm_endpoint: Optional[str] = Field(None, max_length=500)
    base_url: str = Field("http://localhost:1234/v1", max_length=500)
    api_key: str = Field("local-key", max_length=500)
    provider: str = Field("local", max_length=20)


GROQ_ENDPOINT = "https://api.groq.com/openai/v1"
GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEPRECATED_OR_DEFAULT_MODELS = {"", "default", "local-model", "llama3-8b-8192", "llama3-70b-8192"}


def _clean_api_key(raw: Optional[str]) -> str:
    """Nettoie une clé API d'éventuels guillemets, retours chariot ou préfixes copiés par erreur."""
    if raw is None:
        return ""
    s = str(raw).strip().strip("\"'` \t\r\n")
    if s.lower().startswith("bearer "):
        s = s[7:].strip().strip("\"'` \t\r\n")
    if s.startswith("GROQ_API_KEY="):
        s = s[len("GROQ_API_KEY="):].strip().strip("\"'` \t\r\n")
    return s


def _parametres_llm(payload: Any) -> tuple[str, str, str, str]:
    """
    Renvoie (endpoint, clé API, source_clé, modèle) pour l'appel LLM.
    source_clé vaut 'payload', 'env' ou 'default'.

    Règles de priorité stricte :
    1. Si payload.api_key est renseigné et non vide (hors placeholders 'local-key', 'cle-absente') :
       priorité absolue -> api_key = payload.api_key.strip(), source_clé = 'payload'.
    2. Sinon, si provider == 'groq_auto' ou si l'endpoint vise Groq :
       repli sur la variable serveur os.environ.get('GROQ_API_KEY', '').strip(), source_clé = 'env'.
    3. Sinon :
       api_key = user_key or 'local-key', source_clé = 'payload' si user_key else 'default'.
    """
    provider = getattr(payload, "provider", None) or "groq_auto"
    raw_key = getattr(payload, "api_key", None)
    user_key = _clean_api_key(raw_key)

    if provider == "groq_auto":
        endpoint = GROQ_ENDPOINT
    elif provider == "groq":
        endpoint = getattr(payload, "llm_endpoint", None) or GROQ_ENDPOINT
    else:
        endpoint = getattr(payload, "llm_endpoint", None) or getattr(payload, "base_url", None) or "http://localhost:1234/v1"

    is_groq = "api.groq.com" in endpoint or provider in ("groq", "groq_auto")

    if user_key and user_key not in ("local-key", "cle-absente"):
        api_key = user_key
        key_source = "payload"
    elif is_groq:
        raw_env = os.getenv("GROQ_API_KEY") or os.getenv("VITE_GROQ_API_KEY") or os.getenv("GROQ_KEY") or ""
        env_key = _clean_api_key(raw_env)
        api_key = env_key
        key_source = "env"
        if not env_key:
            logging.warning("Mode groq_auto demandé mais GROQ_API_KEY absente de l'environnement serveur.")
    else:
        api_key = user_key or "local-key"
        key_source = "payload" if user_key else "default"

    raw_model = getattr(payload, "model", None)
    model_str = str(raw_model).strip() if raw_model is not None else ""

    if is_groq:
        if not model_str or model_str in DEPRECATED_OR_DEFAULT_MODELS:
            model = GROQ_DEFAULT_MODEL
        else:
            model = model_str
    else:
        model = model_str or "local-model"

    return endpoint, api_key, key_source, model


def _inject_textes_reference(enriched_list: list[EnrichedAmendment], textes_ref: dict[str, str]):
    """Injecte le texte initial du projet de loi correspondant à l'article visé."""
    if not textes_ref:
        return
    for a in enriched_list:
        if a.article_vise and not a.texte_loi_reference:
            matched = match_article_reference(textes_ref, a.article_vise)
            if matched:
                a.texte_loi_reference = matched


def _resoudre_commission(am: dict, dispositif: Any, expose: Any) -> dict:
    """
    Résout la commission saisie et corrèle son périmètre thématique au texte.

    Encapsulé ici pour que `_build_enriched` reste lisible et pour garantir
    qu'une défaillance du résolveur ne casse jamais la construction de
    l'amendement (retour de champs vides plutôt qu'exception).
    """
    try:
        source = dict(am)
        # On fournit le texte au résolveur sous les clés qu'il sait lire.
        source.setdefault("dispositif", dispositif or "")
        source.setdefault("exposeSommaire", expose or "")
        return resoudre_commission_et_mots_cles(source)
    except Exception as exc:  # noqa: BLE001
        logging.warning(f"⚠️ Résolution commission ignorée ({exc}).")
        return {
            "commission_ref": "", "commission_libelle": "", "commission_abrege": "",
            "commission_mots_cles": [], "commission_hors_champ": False,
        }


def _build_enriched(raw: dict, index: int) -> EnrichedAmendment:
    """
    Convertit un amendement brut (format AN / normalisé) en EnrichedAmendment Pydantic.
    Tolère les données manquantes grâce aux valeurs par défaut du schéma.
    """
    am = raw.get("amendement", raw)

    # ── Identifiants ──
    uid = am.get("uid") or am.get("id") or raw.get("id") or f"amdt-{index}"
    numero = str(am.get("identification", {}).get("numeroLong", "") or am.get("numero", "") or raw.get("numero", ""))

    # ── Texte juridique universel (tous chemins vérifiés) ──
    dispositif_raw = extract_dispositif_raw(am) or extract_dispositif_raw(raw) or am.get("texte", "") or raw.get("texte", "")
    expose = extract_expose_sommaire(am) or extract_expose_sommaire(raw)

    # ── Division / Article ──
    division = am.get("pointeurFragmentTexte", {}).get("division", {})
    raw_article = division.get("articleDesignationCourte", "") or division.get("titre", "") or am.get("article", "") or raw.get("article", "")
    article = format_article_title(raw_article)

    # ── Auteur et Groupe ──
    signataires = am.get("signataires", {}) or raw.get("signataires", {})
    auteur_block = signataires.get("auteur", {}) if isinstance(signataires, dict) else {}
    auteur_ref = auteur_block.get("acteurRef", "") if isinstance(auteur_block, dict) else (am.get("auteur_ref") or "")
    groupe_ref = (
        auteur_block.get("groupePolitiqueRef", "") if isinstance(auteur_block, dict) else ""
    ) or am.get("groupePolitiqueRef", "") or raw.get("groupRef", "") or ""

    # Détection de groupe politique officiel en priorité absolue
    groupe_nom = ""
    if groupe_ref and str(groupe_ref) in MAPPING_ORGANES_XVII:
        groupe_nom = MAPPING_ORGANES_XVII[str(groupe_ref)]

    # Repli : résolution via le référentiel local des députés.
    # Sans cela, le groupe politique reste vide dès que l'amendement ne porte
    # pas de `groupePolitiqueRef` explicite — c'est-à-dire la majorité des
    # imports réels. Le résolveur sait retrouver le groupe À LA FOIS par
    # matricule (PA841701 -> EcoS) et par nom (« Mme Cathala » -> LFI-NFP),
    # le tout hors-ligne depuis api/data/deputes_active.json.
    # ⚠️ Ne JAMAIS écraser un groupe explicitement fourni par la source : la
    # recherche par nom est approximative (homonymes) et dégraderait une donnée
    # déjà fiable. Le repli ne sert que lorsque tout le reste est vide.
    groupe_explicite = (
        am.get("groupe_politique", "") or raw.get("groupe_politique", "") or raw.get("groupe", "") or ""
    )
    if not groupe_nom and not groupe_explicite:
        try:
            source_signataires = signataires or auteur_ref or am.get("auteurs") or raw.get("auteurs")
            if source_signataires:
                resolu = resolve_signataires(source_signataires)
                groupe_nom = resolu.get("groupe_principal", "") or ""
                # Si on a identifié le groupe sans en connaître la clé, on la
                # complète depuis la fiche du député (utile au <PoliticalGroupTag>).
                if groupe_nom and not groupe_ref and auteur_ref:
                    fiche = get_depute_info(str(auteur_ref)) or {}
                    groupe_ref = fiche.get("organeRef", "") or groupe_ref
        except Exception as exc:  # noqa: BLE001
            logging.debug(f"Résolution groupe politique ignorée : {exc}")

    # ── Détection de qualité Rapporteur / Commission ──
    qualite_auteur = str(auteur_block.get("qualite") or "").lower()
    is_rapporteur = "rapporteur" in qualite_auteur or "commission" in qualite_auteur
    if not is_rapporteur:
        auteurs_list = am.get("auteurs") or raw.get("auteurs", [])
        if auteurs_list:
            auteurs_join = " ".join(str(x) for x in auteurs_list).lower()
            if "rapporteur" in auteurs_join or "commission" in auteurs_join:
                is_rapporteur = True

    # ── Identiques officiels ──
    est_identique = bool(am.get("discussionIdentique") or am.get("estIdentique") or am.get("est_identique_officiel"))
    id_discussion = am.get("idDiscussionIdentique") or am.get("id_discussion_identique")

    # ── Rattachement de sous-amendement et détection gage ──
    p_ref = (
        am.get("amendementParentRef")
        or raw.get("amendementParentRef")
        or am.get("amendement_parent_ref")
        or raw.get("amendement_parent_ref")
    )
    amendement_parent_ref = None
    if isinstance(p_ref, dict):
        if p_ref.get("@xsi:nil") != "true" and p_ref.get("@nil") != "true":
            amendement_parent_ref = p_ref.get("#text") or p_ref.get("uid") or None
    elif isinstance(p_ref, str) and p_ref.strip() and p_ref.lower() not in ("none", "null", "false"):
        amendement_parent_ref = p_ref.strip()

    est_gage = detect_gage_financier(dispositif_raw, raw)

    return EnrichedAmendment(
        amendement_uid=str(uid),
        numero_long=numero,
        dispositif_raw=str(dispositif_raw) if dispositif_raw else "",
        expose_sommaire=str(expose) if expose else "",
        article_vise=str(article) if article else "",
        auteur_ref=str(auteur_ref),
        auteur_nom=am.get("auteur_nom", "") or raw.get("auteur_nom", "") or "",
        auteur_prenom=am.get("auteur_prenom", "") or raw.get("auteur_prenom", "") or "",
        auteur_trigramme=am.get("auteur_trigramme", "") or raw.get("auteur_trigramme", "") or "",
        auteurs_raw=am.get("auteurs", []) or raw.get("auteurs", []),
        groupe_politique_ref=str(groupe_ref),
        groupe_politique=groupe_nom or am.get("groupe_politique", "") or raw.get("groupe_politique", "") or raw.get("groupe", "") or "",
        dossier_ref=am.get("texteLegislatifRef", "") or am.get("dossier_ref", "") or raw.get("dossier_ref", "") or "",
        dossier_titre=am.get("dossier_titre", "") or raw.get("title", "") or "",
        est_identique_officiel=est_identique,
        id_discussion_identique=str(id_discussion) if id_discussion else None,
        est_rapporteur=is_rapporteur,
        amendement_parent_ref=amendement_parent_ref,
        est_gage=est_gage,
        # ── Commission + corrélation thématique (résolu hors-ligne) ──
        **_resoudre_commission(am, dispositif_raw, expose),
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

        # ── Commission + thèmes corrélés (pour <CommissionKeywords>) ──
        "commission_ref": amend.commission_ref,
        "commission": amend.commission_abrege or amend.commission_libelle,
        "commission_libelle": amend.commission_libelle,
        "commission_mots_cles": amend.commission_mots_cles,
        "commission_hors_champ": amend.commission_hors_champ,

        # ── Identiques officiels (pour <IdentiqueAlert>) ──
        "isIdentical": amend.est_identique_officiel,
        "discussionId": amend.id_discussion_identique,

        # ── Gage financier (Art. 40) et sous-amendements ──
        "est_gage": amend.est_gage,
        "amendement_parent_ref": amend.amendement_parent_ref,
        "amendementParentRef": amend.amendement_parent_ref,

        # ── Texte juridique assaini ──
        "dispositif": strip_html_for_display(amend.dispositif_raw or amend.dispositif_clean),
        "dispositif_clean": amend.dispositif_clean,
        "texte": strip_html_for_display(amend.dispositif_raw or amend.dispositif_clean),
        "expose_sommaire": strip_html_for_display(amend.expose_sommaire),

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
        elif amend.statut_mecanique == StatutMecanique.DOUBLON_MECANIQUE:
            # Même texte, même auteur : copie à retirer (« Supprimer les doublons »).
            statut_display = "Doublon"
            couleur = amend.alerte_couleur or "orange"
            intention = f"Détecté mécaniquement : {amend.justification_mecanique}"
            politique = "Classification déterministe (100 % fiable, sans IA)."
            confiance = 1.0
        else:
            statut_display = "Identique" # Strict mapping anti-jargon
            couleur = amend.alerte_couleur or "rouge"
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
        if amend.skip_llm:
            is_identique_ref = bool(amend.groupe_identique_id or "identique" in (amend.justification_mecanique or "").lower())
            statut_display = "Identique" if is_identique_ref else "Isolé"
            couleur = "rouge" if is_identique_ref else "gris"
            justif = amend.justification_mecanique or "Amendement classé par filtrage déterministe."
            base["resultat_ia"] = {
                "id": amend.amendement_uid,
                "statut": statut_display,
                "justification": justif,
                "alerte_couleur": couleur,
                "analyse_intention": f"Détecté mécaniquement : {justif}",
                "analyse_politique": "Classification déterministe (100 % fiable, sans IA).",
                "niveau_confiance": 1.0,
            }
        else:
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

        # ── Phase 3 : Filtre sémantique LLM (uniquement sur les NOUVEAUX non résolus mécaniquement) ──
        nouveaux_count = sum(1 for a in enriched if a.statut_mecanique == StatutMecanique.NOUVEAU and not a.skip_llm)
        processed_llm = [0] # Liste pour mutabilité dans process_llm
        
        # Sémaphore pour limiter le nombre de requêtes simultanées
        semaphore = asyncio.Semaphore(2)
        
        async def process_llm(amend: EnrichedAmendment, rang: int) -> dict:
            llm_data = None
            if amend.statut_mecanique == StatutMecanique.NOUVEAU and not amend.skip_llm:
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
                            endpoint_llm, cle_llm, source_cle, modele_llm = _parametres_llm(payload)
                            valid_endpoint = validate_endpoint_url(endpoint_llm)
                            resultat = await asyncio.to_thread(
                                evaluate_similitude,
                                amend_dict, candidats,
                                llm_endpoint=valid_endpoint,
                                model=modele_llm, api_key=cle_llm,
                                key_source=source_cle,
                                timeout=120.0, max_tokens=payload.max_tokens, temperature=payload.temperature,
                                texte_loi_reference=amend.texte_loi_reference,
                            )
                            llm_data = resultat.model_dump()
                            save_classification(amend.amendement_uid, llm_data)
                        except Exception as exc:
                            clean_exc = sanitize_log_message(str(exc), cle_llm)
                            logging.error(f"❌ LLM FAIL {amend.amendement_uid} : {clean_exc}")
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
                    endpoint_llm, cle_llm, source_cle, modele_llm = _parametres_llm(payload)
                    valid_endpoint = validate_endpoint_url(endpoint_llm)

                    if "api.groq.com" in valid_endpoint and not cle_llm:
                        if source_cle == "payload":
                            raise HTTPException(status_code=401, detail="Clé API Groq personnelle invalide ou expirée")
                        else:
                            raise HTTPException(
                                status_code=503,
                                detail="La clé Groq de la démo n'est pas encore configurée sur le serveur (GROQ_API_KEY).",
                            )

                    resultat = await asyncio.to_thread(
                        evaluate_similitude,
                        amend_dict, candidats,
                        llm_endpoint=valid_endpoint,
                        model=modele_llm, api_key=cle_llm,
                        key_source=source_cle,
                        timeout=120.0, max_tokens=payload.max_tokens, temperature=payload.temperature,
                        texte_loi_reference=target.texte_loi_reference,
                    )

                    if "Clé API Groq personnelle invalide ou expirée" in resultat.analyse_intention:
                        raise HTTPException(status_code=401, detail="Clé API Groq personnelle invalide ou expirée")
                    elif "Clé API Groq Vercel du projet invalide" in resultat.analyse_intention:
                        raise HTTPException(status_code=401, detail="Clé API Groq Vercel du projet invalide")

                    llm_data = resultat.model_dump()
                    save_classification(target.amendement_uid, llm_data)
                except HTTPException:
                    raise
                except Exception as exc:
                    clean_exc = sanitize_log_message(str(exc), cle_llm)
                    logging.error(f"❌ LLM FAIL {target.amendement_uid} : {clean_exc}")
                    exc_str = clean_exc
                    exc_name = type(exc).__name__
                    if (
                        "AuthenticationError" in exc_name
                        or "PermissionDeniedError" in exc_name
                        or "401" in exc_str
                        or "403" in exc_str
                        or "Invalid API Key" in exc_str
                        or "invalid_api_key" in exc_str
                    ):
                        auth_msg = (
                            "Clé API Groq personnelle invalide ou expirée"
                            if source_cle == "payload"
                            else "Clé API Groq Vercel du projet invalide"
                        )
                        raise HTTPException(status_code=401, detail=auth_msg)
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
        
    except HTTPException:
        raise
    except Exception as exc:
        clean_crash = sanitize_log_message(str(exc))
        logging.error(f"❌ V2 LLM CRASH : {clean_crash}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur d'analyse LLM : {clean_crash}")


# ══════════════════════════════════════════════════════════════════════════
# ROUTE V2 — Analyse de Surtransposition et Conformité UE (EUR-Lex / Légifrance)
# ══════════════════════════════════════════════════════════════════════════

_SURTRANSPOSITION_CHECKER: Optional[Any] = None


def get_surtransposition_checker():
    global _SURTRANSPOSITION_CHECKER
    if _SURTRANSPOSITION_CHECKER is None:
        try:
            from api.services.analysis.surtransposition_checker import SurtranspositionChecker
        except ModuleNotFoundError:
            from services.analysis.surtransposition_checker import SurtranspositionChecker
        _SURTRANSPOSITION_CHECKER = SurtranspositionChecker()
    return _SURTRANSPOSITION_CHECKER


@app.post("/api/v2/resumer")
async def v2_resumer(payload: ResumeRequest):
    """
    Résumé neutre d'un amendement (1 à 2 phrases), à la demande depuis la
    fiche de détail. Même choix d'IA que le classement (locale, clé
    utilisateur ou « Groq (Démo) » avec la clé du serveur).
    """
    endpoint_llm, cle_llm, source_cle, modele_llm = _parametres_llm(payload)
    if "api.groq.com" in endpoint_llm and not cle_llm:
        if source_cle == "payload":
            raise HTTPException(status_code=401, detail="Clé API Groq personnelle invalide ou expirée")
        else:
            raise HTTPException(
                status_code=503,
                detail="La clé Groq de la démo n'est pas encore configurée sur le serveur (GROQ_API_KEY).",
            )
    try:
        resume = await asyncio.to_thread(
            resumer_amendement,
            _nettoyer_html(payload.dispositif),
            _nettoyer_html(payload.expose_sommaire or ""),
            payload.article,
            payload.texte_loi_reference,
            endpoint_llm,
            model=modele_llm,
            api_key=cle_llm,
            key_source=source_cle,
        )
    except RuntimeError as exc:
        message = sanitize_log_message(str(exc), cle_llm)
        logging.warning(f"⚠️ Résumé impossible ({payload.amendement_uid}) : {message}")
        if (
            "Clé API Groq" in message
            or "401" in message
            or "403" in message
            or "invalide" in message.lower()
        ):
            auth_msg = (
                "Clé API Groq personnelle invalide ou expirée"
                if source_cle == "payload"
                else "Clé API Groq Vercel du projet invalide"
            )
            raise HTTPException(status_code=401, detail=auth_msg)
        raise HTTPException(status_code=502, detail=message)
    return {"amendement_uid": payload.amendement_uid, "resume": resume}


@app.post("/api/v2/surtransposition")
async def v2_surtransposition(payload: SurtranspositionRequest):
    """
    Analyse de conformité européenne et détection de surtransposition.
    Effectue une comparaison RAG en local contre les directives européennes (indexées depuis EUR-Lex)
    avec détection heuristique et évaluation LLM déterministe.
    """
    try:
        checker = get_surtransposition_checker()

        # Cas 1 : Batch de plusieurs amendements
        if payload.amendements:
            results = []
            for am in payload.amendements:
                disp = extract_dispositif_raw(am) or am.get("dispositif") or ""
                expose = extract_expose_sommaire(am) or am.get("expose_sommaire") or am.get("exposeSommaire") or ""
                full_text = f"{disp}\n{expose}".strip()
                art = am.get("article_vise") or am.get("article") or ""
                celex = am.get("celex_id")

                res = await asyncio.to_thread(
                    checker.analyze_amendment,
                    amendment_text=full_text,
                    target_article=art,
                    celex_id=celex,
                )
                res_dict = res.model_dump()
                res_dict["amendement_uid"] = am.get("uid") or am.get("id") or am.get("amendement_uid")
                results.append(res_dict)
            return results

        # Cas 2 : Amendement unitaire dans `amendement`
        if payload.amendement:
            am = payload.amendement
            disp = extract_dispositif_raw(am) or am.get("dispositif") or ""
            expose = extract_expose_sommaire(am) or am.get("expose_sommaire") or am.get("exposeSommaire") or ""
            full_text = f"{disp}\n{expose}".strip()
            art = am.get("article_vise") or am.get("article") or ""
            celex = am.get("celex_id")

            res = await asyncio.to_thread(
                checker.analyze_amendment,
                amendment_text=full_text,
                target_article=art,
                celex_id=celex,
            )
            res_dict = res.model_dump()
            res_dict["amendement_uid"] = am.get("uid") or am.get("id") or am.get("amendement_uid")
            return res_dict

        # Cas 3 : Paramètres à plat
        full_text = f"{payload.dispositif or ''}\n{payload.expose_sommaire or ''}".strip()
        res = await asyncio.to_thread(
            checker.analyze_amendment,
            amendment_text=full_text,
            target_article=payload.article_vise,
            celex_id=payload.celex_id,
        )
        res_dict = res.model_dump()
        if payload.amendement_uid:
            res_dict["amendement_uid"] = payload.amendement_uid
        return res_dict

    except HTTPException:
        raise
    except Exception as exc:
        clean_msg = sanitize_log_message(str(exc))
        logging.warning(f"⚠️ Repli gracieux surtransposition : {clean_msg}")
        return {
            "amendement_uid": payload.amendement_uid,
            "status": "STRICT_TRANSPOSITION",
            "confidence": 0.5,
            "delta_summary": "Aucune exigence excédant le socle réglementaire européen détectée (mode heuristique).",
            "matched_sources": [],
            "target_article": payload.article_vise,
            "analysis_mode": "HEURISTIC_FALLBACK",
        }
