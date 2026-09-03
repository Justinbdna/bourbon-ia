"""
api/deputes_resolver.py — Résolveur local des députés et groupes politiques (Tricoteuses)
==========================================================================================
Permet la résolution O(1) locale des identifiants parlementaires (PA...) et groupes
sans dépendre du réseau ni lever d'exception en cas d'inconnu.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("bourbon.deputes")

CURRENT_DIR = Path(__file__).resolve().parent
DATA_PATH = CURRENT_DIR / "data" / "deputes_active.json"

# ── Dictionnaire officiel des organes politiques (XVIIe Législature) ──
ORGANES_GROUPES_MAP: dict[str, str] = {
    "PO845401": "EPR",      # Ensemble Pour la République
    "PO845407": "RN",       # Rassemblement National
    "PO845413": "LFI-NFP",  # La France Insoumise - Nouveau Front Populaire
    "PO845419": "SOC",      # Socialistes et apparentés
    "PO845425": "DR",       # Droite Républicaine
    "PO845439": "EcoS",     # Écologiste et Social
    "PO845454": "Dem",      # Les Démocrates
    "PO845470": "HOR",      # Horizons & Indépendants
    "PO845485": "LIOT",     # Libertés, Indépendants, Outre-mer et Territoires
    "PO845500": "GDR",      # Gauche Démocrate et Républicaine
    "PO845517": "UDR",      # Union des Droites pour la République
    "PO793087": "NI",       # Non inscrits
    "NI": "Non inscrit",
}

_DEPUTES_DB: Optional[dict[str, dict[str, str]]] = None


def _load_deputes_db() -> dict[str, dict[str, str]]:
    """Charge le snapshot local des députés (singleton en mémoire avec fallback total)."""
    global _DEPUTES_DB
    if _DEPUTES_DB is not None:
        return _DEPUTES_DB

    _DEPUTES_DB = {}
    try:
        if DATA_PATH.is_file():
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                _DEPUTES_DB = json.load(f)
                logger.info(f"🏛️ Référentiel députés chargé ({DATA_PATH}) : {len(_DEPUTES_DB)} entrées.")
        else:
            logger.warning(f"⚠️ Fichier députés introuvable sur {DATA_PATH}. Mode dégradé activé (zéro plantage).")
    except (FileNotFoundError, Exception) as exc:
        logger.warning(f"⚠️ Erreur chargement deputes_active.json ({exc}). Mode dégradé activé.")
        _DEPUTES_DB = {}

    return _DEPUTES_DB


def get_depute_info(acteur_ref: str) -> Optional[dict[str, str]]:
    """Retourne la fiche d'un député par son matricule PA... ou None."""
    db = _load_deputes_db()
    return db.get(acteur_ref)


def resolve_single_signataire(raw_signataire: Any) -> tuple[str, str, bool]:
    """
    Résout un signataire individuel.

    Returns:
        tuple (nom_affiche, groupe_acronyme, is_rapporteur)
    """
    db = _load_deputes_db()
    is_rapporteur = False

    if isinstance(raw_signataire, dict):
        # Format Tricoteuses : {"acteurRef": "PA...", "qualite": "Rapporteur", ...}
        acteur_ref = str(raw_signataire.get("acteurRef") or raw_signataire.get("uid") or "")
        qualite = str(raw_signataire.get("qualite") or "").lower()
        if "rapporteur" in qualite or "commission" in qualite:
            is_rapporteur = True

        if acteur_ref and acteur_ref in db:
            dep = db[acteur_ref]
            nom = dep.get("nom", acteur_ref)
            groupe = dep.get("groupe") or ORGANES_GROUPES_MAP.get(dep.get("organeRef", ""), "")
            return nom, groupe, is_rapporteur
        elif acteur_ref:
            # Fallback gracieux sans lever d'erreur
            nom = raw_signataire.get("nom") or acteur_ref
            groupe = raw_signataire.get("groupe") or ""
            return nom, groupe, is_rapporteur

    raw_str = str(raw_signataire or "").strip()
    if not raw_str:
        return "", "", False

    if "rapporteur" in raw_str.lower() or "commission" in raw_str.lower():
        is_rapporteur = True

    # Si c'est un identifiant exact PA...
    if raw_str in db:
        dep = db[raw_str]
        nom = dep.get("nom", raw_str)
        groupe = dep.get("groupe") or ORGANES_GROUPES_MAP.get(dep.get("organeRef", ""), "")
        return nom, groupe, is_rapporteur

    # Recherche par nom ou sous-chaîne dans la base
    clean_lower = raw_str.lower()
    for pa_id, dep in db.items():
        dep_nom = dep.get("nom", "").lower()
        # Correspondance exacte ou partielle significative
        if dep_nom and (dep_nom in clean_lower or any(part in clean_lower for part in dep_nom.split() if len(part) > 3)):
            groupe = dep.get("groupe") or ORGANES_GROUPES_MAP.get(dep.get("organeRef", ""), "")
            return raw_str, groupe, is_rapporteur

    # Fallback : texte brut
    return raw_str, "", is_rapporteur


def resolve_signataires(signataires_raw: Any) -> dict[str, Any]:
    """
    Résout une structure de signataires (list, str ou dict) et retourne :
      - auteurs_formatte : chaîne lisible (ex: "Laurent Monnier (EPR), Léa Balage (EcoS)")
      - groupe_principal : acronyme du groupe du 1er signataire
      - est_rapporteur : bool (True si rapporteur/commission détecté)
    """
    if not signataires_raw:
        return {
            "auteurs_formatte": "",
            "groupe_principal": "",
            "est_rapporteur": False,
        }

    try:
        items_to_resolve: list[Any] = []
        global_rapporteur = False

        if isinstance(signataires_raw, dict):
            # Format complet Tricoteuses : {"auteur": {...}, "cosignataires": [...]}
            auteur_block = signataires_raw.get("auteur", {})
            if isinstance(auteur_block, dict):
                qualite = str(auteur_block.get("qualite") or "").lower()
                if "rapporteur" in qualite or "commission" in qualite:
                    global_rapporteur = True
                items_to_resolve.append(auteur_block)

            cosignataires = signataires_raw.get("cosignataires") or signataires_raw.get("coSignataires") or []
            if isinstance(cosignataires, list):
                items_to_resolve.extend(cosignataires)
            elif isinstance(cosignataires, str):
                items_to_resolve.append(cosignataires)

            texte_libre = str(signataires_raw.get("texte") or "")
            if "rapporteur" in texte_libre.lower() or "commission" in texte_libre.lower():
                global_rapporteur = True
        elif isinstance(signataires_raw, list):
            items_to_resolve.extend(signataires_raw)
        else:
            # Chaîne brute (éventuellement séparée par des virgules)
            str_val = str(signataires_raw)
            if "rapporteur" in str_val.lower() or "commission" in str_val.lower():
                global_rapporteur = True
            if "," in str_val:
                items_to_resolve.extend([part.strip() for part in str_val.split(",") if part.strip()])
            else:
                items_to_resolve.append(str_val)

        resolus = []
        groupe_principal = ""

        for item in items_to_resolve:
            nom, grp, is_rap = resolve_single_signataire(item)
            if is_rap:
                global_rapporteur = True
            if not groupe_principal and grp:
                groupe_principal = grp

            if nom:
                if grp:
                    resolus.append(f"{nom} ({grp})")
                else:
                    resolus.append(nom)

        auteurs_formatte = ", ".join(resolus) if resolus else (str(signataires_raw) if not isinstance(signataires_raw, (dict, list)) else "")

        return {
            "auteurs_formatte": auteurs_formatte,
            "groupe_principal": groupe_principal,
            "est_rapporteur": global_rapporteur,
        }
    except Exception as exc:
        logger.warning(f"⚠️ Erreur inattendue resolve_signataires ({exc}). Mode dégradé sans crash.")
        return {
            "auteurs_formatte": str(signataires_raw) if signataires_raw and not isinstance(signataires_raw, (dict, list)) else "",
            "groupe_principal": "",
            "est_rapporteur": False,
        }
