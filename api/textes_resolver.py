"""
api/textes_resolver.py — Résolveur local de dossier législatif et textes de référence
====================================================================================
Permet d'extraire automatiquement l'identifiant de texte législatif (texteLegislatifRef)
depuis une liasse d'amendements, de charger les articles d'origine de la loi et de
les associer de manière déterministe et tolérante aux amendements visés.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("bourbon.textes")

CURRENT_DIR = Path(__file__).resolve().parent
TEXTES_DIR = CURRENT_DIR / "data" / "textes"

# ── Cache mémoire singleton ──
_TEXTES_CACHE: dict[str, dict[str, str]] = {}


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


def get_textes_reference(texte_ref_id: str) -> dict[str, str]:
    """
    Retourne le dictionnaire des articles de référence pour un identifiant de loi donné.
    Retourne {} sans lever d'exception en cas de fichier absent ou invalide.
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
        logger.warning(f"⚠️ Aucun fichier de texte de référence trouvé pour '{clean_id}' sur {TEXTES_DIR}.")
        _TEXTES_CACHE[clean_id] = {}
        return {}

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
