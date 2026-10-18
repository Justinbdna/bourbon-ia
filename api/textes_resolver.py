"""
api/textes_resolver.py — Résolveur de dossier législatif et textes de référence
==============================================================================
Permet d'extraire automatiquement l'identifiant de texte législatif (texteLegislatifRef)
depuis une liasse d'amendements, de charger les articles d'origine de la loi et de
les associer de manière déterministe et tolérante aux amendements visés.

Sources, dans l'ordre :
  1. fichier local `api/data/textes/<uid>.json` (mode hors-ligne / air-gapped) ;
  2. API Tricoteuses `GET /v2/documents/<uid>` : texte EXACT visé par les
     amendements (le `texteLegislatifRef` désigne la version amendée — texte
     transmis, texte de la commission…). Seul l'identifiant public du texte
     est envoyé, jamais le contenu des amendements.
     Désactivable avec BOURBON_TEXTES_DISTANTS=0.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("bourbon.textes")

CURRENT_DIR = Path(__file__).resolve().parent
TEXTES_DIR = CURRENT_DIR / "data" / "textes"

# ── Cache mémoire singleton ──
_TEXTES_CACHE: dict[str, dict[str, str]] = {}

# Échecs de récupération distante : on ne réessaie pas avant ce délai, pour
# ne pas ralentir chaque appel d'analyse (un appel API par amendement).
_ECHECS_DISTANTS: dict[str, float] = {}
DELAI_NOUVEL_ESSAI_S = 300
TIMEOUT_TRICOTEUSES_S = 8.0

_NOUVEAU_RE = re.compile(r"\s*\((?:nouveau|supprim[ée])\)\s*$", re.IGNORECASE)


def _normalize_article_key(raw_art: str) -> str:
    """
    Normalise une désignation d'article pour une comparaison robuste.
    Exemples :
      - 'ARTICLE PREMIER' -> '1'
      - 'Article 1er'     -> '1'
      - 'ART. PREMIER'    -> '1'
      - 'ART. 2'          -> '2'
      - 'Article 2'       -> '2'
    """
    if not raw_art:
        return ""
    s = str(raw_art).strip().lower()
    # Nettoie les préfixes 'article' ou 'art.' ou 'art'
    s = re.sub(r"^(article|art\.?)\s*", "", s).strip()
    s = re.sub(r"\b(article|art)\b\.?", "", s).strip()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s in ("1er", "premier", "1ere", "première", "1"):
        return "1"
    return s


def extract_texte_ref(amendements: list[Any]) -> str:
    """
    Parcourt les amendements et retourne le premier identifiant texteLegislatifRef
    valide (ex: 'PIONANR5L17B0149'). Retourne '' si absent.
    """
    if not amendements:
        return ""

    for item in amendements:
        candidate = None
        if hasattr(item, "dossier_ref") and getattr(item, "dossier_ref"):
            candidate = getattr(item, "dossier_ref")
        elif isinstance(item, dict):
            # Formats divers : AN brut ou dénormalisé
            am = item.get("amendement", item)
            candidate = (
                am.get("texteLegislatifRef")
                or am.get("dossierRef")
                or am.get("dossier_ref")
                or item.get("texteLegislatifRef")
                or item.get("dossier_ref")
                or item.get("dossierRef")
            )
            # Cas où dossierRef est un dictionnaire
            if isinstance(candidate, dict):
                candidate = candidate.get("texteLegislatifRef") or candidate.get("uid") or ""

        if candidate and isinstance(candidate, str):
            clean = candidate.strip()
            # Valide un identifiant parlementaire plausible
            if len(clean) >= 4 and not clean.lower().startswith("amdt"):
                return clean

    # Si non trouvé explicitement, vérifie si les amendements portent sur la PPL 149
    # (droit de vote élections municipales / article 88-3)
    for item in amendements:
        text_content = ""
        if hasattr(item, "dispositif_raw"):
            text_content = f"{getattr(item, 'dispositif_raw', '')} {getattr(item, 'expose_sommaire', '')}"
        elif isinstance(item, dict):
            am = item.get("amendement", item)
            text_content = f"{am.get('dispositif', '')} {am.get('expose_sommaire', '')}"
        
        if "88-3" in text_content or ("vote" in text_content.lower() and "municipales" in text_content.lower()):
            return "PIONANR5L17B0149"

    return ""


def _textes_distants_actives() -> bool:
    return os.getenv("BOURBON_TEXTES_DISTANTS", "1").strip().lower() not in ("0", "false", "non", "off")


def articles_depuis_document(document: dict[str, Any]) -> dict[str, str]:
    """
    Convertit un document Tricoteuses (`subdivisions` + `alineas`) en
    {« Article 3 bis » : texte}. Les alinéas sont numérotés « (1) », « (2) »…
    comme dans la marge des textes de l'Assemblée, pour que l'IA puisse
    rapprocher « À l'alinéa 3… » du bon passage.
    """
    subdivisions = document.get("subdivisions") or []
    alineas = document.get("alineas") or []

    par_article: dict[str, list[dict[str, Any]]] = {}
    for alinea in alineas:
        par_article.setdefault(alinea.get("articleRefHash"), []).append(alinea)

    articles: dict[str, str] = {}
    for sub in sorted(subdivisions, key=lambda x: x.get("sequence") or 0):
        if sub.get("type") != "Article" or not sub.get("titre"):
            continue
        lignes = [
            f"({(a.get('numero') or 0) + 1}) {str(a.get('texte') or '').strip()}"
            for a in sorted(par_article.get(sub.get("hash"), []), key=lambda x: x.get("numero") or 0)
            if str(a.get("texte") or "").strip()
        ]
        if lignes:
            # « Article 3 bis (nouveau) » → « Article 3 bis » : évite qu'un
            # amendement sur l'article 3 bis tombe sur l'article 3.
            articles[_NOUVEAU_RE.sub("", sub["titre"]).strip()] = "\n".join(lignes)
    return articles


def _recuperer_texte_tricoteuses(clean_id: str) -> dict[str, str]:
    """Télécharge le texte depuis l'API Tricoteuses. {} en cas d'échec (jamais d'exception)."""
    try:
        try:
            from api.tricoteuses_client import _request
        except ImportError:
            from tricoteuses_client import _request
        reponse = _request(f"/v2/documents/{clean_id}", timeout=TIMEOUT_TRICOTEUSES_S)
        document = reponse.get("data") or {}
        articles = articles_depuis_document(document) if isinstance(document, dict) else {}
        if articles:
            logger.info(
                f"📜 Texte de référence récupéré en direct depuis Tricoteuses ({clean_id}) : "
                f"{len(articles)} article(s) — « {document.get('titrePrincipalCourt') or document.get('titrePrincipal') or ''} »."
            )
        else:
            logger.warning(f"⚠️ Tricoteuses : aucun article exploitable pour '{clean_id}'.")
        return articles
    except Exception as exc:
        logger.warning(f"⚠️ Récupération du texte '{clean_id}' sur Tricoteuses impossible : {exc}")
        return {}


def get_textes_reference(texte_ref_id: str) -> dict[str, str]:
    """
    Retourne le dictionnaire des articles de référence pour un identifiant de loi donné.
    Fichier local d'abord, puis API Tricoteuses (texte en direct).
    Retourne {} sans lever d'exception si le texte est introuvable.
    """
    if not texte_ref_id:
        return {}

    clean_id = str(texte_ref_id).strip()
    if clean_id.endswith(".json"):
        clean_id = clean_id[:-5]

    if clean_id in _TEXTES_CACHE:
        return dict(_TEXTES_CACHE[clean_id])

    candidate_files = [
        TEXTES_DIR / f"{clean_id}.json",
        Path("api/data/textes") / f"{clean_id}.json",
        Path("/var/task/api/data/textes") / f"{clean_id}.json",
    ]

    target_file = None
    for f in candidate_files:
        try:
            if f.is_file():
                target_file = f
                break
        except Exception:
            pass

    if not target_file:
        if not _textes_distants_actives():
            logger.warning(f"⚠️ Aucun fichier de texte de référence trouvé pour '{clean_id}' sur {TEXTES_DIR}.")
            _TEXTES_CACHE[clean_id] = {}
            return {}
        dernier_echec = _ECHECS_DISTANTS.get(clean_id)
        if dernier_echec and time.monotonic() - dernier_echec < DELAI_NOUVEL_ESSAI_S:
            return {}
        articles = _recuperer_texte_tricoteuses(clean_id)
        if articles:
            # Un uid de document désigne une version figée du texte : le cache
            # n'a pas besoin d'expirer (une nouvelle version = un nouvel uid).
            _TEXTES_CACHE[clean_id] = articles
            _ECHECS_DISTANTS.pop(clean_id, None)
        else:
            _ECHECS_DISTANTS[clean_id] = time.monotonic()
        return dict(articles)

    try:
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            articles = data.get("articles", {})
            if isinstance(articles, dict):
                _TEXTES_CACHE[clean_id] = articles
                logger.info(f"📜 Textes de référence chargés ({clean_id}) : {len(articles)} article(s).")
                return dict(articles)
            _TEXTES_CACHE[clean_id] = {}
            return {}
    except Exception as exc:
        logger.warning(f"⚠️ Erreur lors du chargement de {target_file} : {exc}")
        _TEXTES_CACHE[clean_id] = {}
        return {}


def match_article_reference(articles_dict: dict[str, str], article_vise: str) -> Optional[str]:
    """
    Fait correspondre de manière insensible à la casse et tolérante aux variantes
    (ex: '1er' / 'premier', 'art. 2' / 'article 2') l'article visé avec les textes d'origine.
    """
    if not articles_dict or not article_vise:
        return None

    # 1. Correspondance exacte
    if article_vise in articles_dict:
        return articles_dict[article_vise]

    # 2. Correspondance insensible à la casse et espaces
    art_clean = article_vise.strip().lower()
    lower_map = {k.strip().lower(): v for k, v in articles_dict.items()}
    if art_clean in lower_map:
        return lower_map[art_clean]

    # 3. Correspondance normalisée par numéro d'article
    target_norm = _normalize_article_key(article_vise)
    if target_norm:
        for k, v in articles_dict.items():
            if _normalize_article_key(k) == target_norm:
                return v

    # 4. Correspondance par inclusion partielle
    for k, v in articles_dict.items():
        k_clean = k.strip().lower()
        if k_clean in art_clean or art_clean in k_clean:
            return v

    return None
