"""
api/deputes_resolver.py — Résolveur local des députés et groupes politiques (Tricoteuses)
==========================================================================================
Permet la résolution O(1) locale des identifiants parlementaires (PA...) et groupes
sans dépendre du réseau ni lever d'exception en cas d'inconnu.

Deux référentiels :
  • deputes_active.json     — députés en exercice (prioritaire) ;
  • deputes_historique.json — tous les députés depuis 1997 (jeu officiel AMO30,
    cf. scripts/construire_deputes_historique.py), en repli pour les cosignataires
    ayant quitté l'Assemblée. Il ne sert qu'à la recherche par matricule et par
    nom complet exact : la recherche approchée (nom de famille) reste limitée aux
    députés en exercice, pour ne pas confondre des homonymes d'autres législatures.
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
DATA_PATH_HISTORIQUE = CURRENT_DIR / "data" / "deputes_historique.json"

# ── Dictionnaire officiel des organes politiques (XVIIe Législature & Sénat) ──
MAPPING_ORGANES_XVII: dict[str, str] = {
    # Assemblée nationale XVIIe & XVIe
    "PO845401": "RN",       # Rassemblement National
    "PO845407": "EPR",      # Ensemble pour la République
    "PO845413": "LFI-NFP",  # La France Insoumise - Nouveau Front Populaire
    "PO845419": "SOC",      # Socialistes et apparentés
    "PO845425": "DR",       # Droite Républicaine
    "PO845439": "EcoS",     # Écologiste et Social
    "PO845454": "Dem",      # Les Démocrates
    "PO845470": "HOR",      # Horizons & Indépendants
    "PO845485": "LIOT",     # Libertés, Indépendants, Outre-mer et Territoires
    "PO845514": "GDR",      # Gauche Démocrate et Républicaine (Tricoteuses)
    "PO845500": "GDR",      # Gauche Démocrate et Républicaine
    "PO845517": "UDR",      # Union des Droites pour la République
    "PO872880": "UDR",      # Union des Droites pour la République (Tricoteuses)
    "PO847173": "UDR",      # Union des Droites pour la République
    "PO840056": "NI",       # Non inscrits
    "PO793087": "NI",       # Non inscrits (XVIe)
    "NI": "Non inscrit",
    # Sénat (organes politiques)
    "PO77710": "LR",        # Les Républicains (Sénat)
    "PO77714": "SER",       # Socialiste, Écologiste et Républicain (Sénat)
    "PO77708": "UC",        # Union Centriste (Sénat)
    "PO77724": "RDPI",      # Rassemblement des démocrates, progressistes et indépendants (Sénat)
    "PO77720": "CRCE-K",    # Communiste républicain citoyen et écologiste (Sénat)
    "PO77717": "RDSE",      # Rassemblement Démocratique et Social Européen (Sénat)
    "PO77722": "LIRT",      # Les Indépendants - République et Territoires (Sénat)
    "PO77725": "GEST",      # Écologiste - Solidarité et Territoires (Sénat)
    "PO77726": "NI",        # Non-inscrits (Sénat)
    # Exécutif / Institutionnel
    "PO791599": "GOUVERNEMENT",
    "GOUV": "GOUVERNEMENT",
    "GOUVERNEMENT": "GOUVERNEMENT",
}
ORGANES_GROUPES_MAP = MAPPING_ORGANES_XVII

_DEPUTES_DB: Optional[dict[str, dict[str, str]]] = None
_DEPUTES_HISTORIQUE: Optional[dict[str, dict[str, Any]]] = None


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


def _load_historique_db() -> dict[str, dict[str, Any]]:
    """Charge le référentiel historique (députés depuis 1997), vide s'il est absent."""
    global _DEPUTES_HISTORIQUE
    if _DEPUTES_HISTORIQUE is not None:
        return _DEPUTES_HISTORIQUE

    _DEPUTES_HISTORIQUE = {}
    try:
        if DATA_PATH_HISTORIQUE.is_file():
            with open(DATA_PATH_HISTORIQUE, "r", encoding="utf-8") as f:
                _DEPUTES_HISTORIQUE = json.load(f)
                logger.info(f"🏛️ Historique des députés chargé : {len(_DEPUTES_HISTORIQUE)} entrées.")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"⚠️ Erreur chargement deputes_historique.json ({exc}). Repli désactivé.")
        _DEPUTES_HISTORIQUE = {}

    return _DEPUTES_HISTORIQUE


def get_depute_info(acteur_ref: str) -> Optional[dict[str, Any]]:
    """Fiche d'un député par son matricule PA… (en exercice, sinon historique) ou None."""
    return _load_deputes_db().get(acteur_ref) or _load_historique_db().get(acteur_ref)


def _groupe_de(dep: dict[str, Any]) -> str:
    return dep.get("groupe") or MAPPING_ORGANES_XVII.get(dep.get("organeRef", ""), "")


def resolve_single_signataire(raw_signataire: Any) -> tuple[str, str, bool]:
    """
    Résout un signataire individuel.
    Returns:
        tuple (nom_affiche, groupe_acronyme, is_rapporteur)
    """
    import html
    db = _load_deputes_db()
    is_rapporteur = False

    if isinstance(raw_signataire, dict):
        type_auteur = str(raw_signataire.get("typeAuteur") or "").strip()
        qualite = str(raw_signataire.get("qualite") or "").strip()
        libelle = html.unescape(str(raw_signataire.get("libelle") or "")).strip()
        nom_dict = html.unescape(str(raw_signataire.get("nom") or "")).strip()

        # Détection Gouvernement
        if (
            type_auteur.lower() == "gouvernement"
            or "gouvernement" in libelle.lower()
            or "gouvernement" in nom_dict.lower()
        ):
            return "le Gouvernement", "GOUVERNEMENT", False

        # Détection Rapporteur / Commission
        if (
            "rapporteur" in type_auteur.lower()
            or "rapporteur" in qualite.lower()
            or "commission" in qualite.lower()
            or "rapporteur" in libelle.lower()
        ):
            is_rapporteur = True

        # 1. Priorité absolue : groupePolitiqueRef natif si présent
        org_ref = str(raw_signataire.get("groupePolitiqueRef") or raw_signataire.get("organeRef") or "")
        groupe_natif = MAPPING_ORGANES_XVII.get(org_ref, "")

        acteur_ref = str(raw_signataire.get("acteurRef") or raw_signataire.get("uid") or "")

        dep = get_depute_info(acteur_ref) if acteur_ref else None
        if dep:
            nom = dep.get("nom", acteur_ref)
            groupe = groupe_natif or _groupe_de(dep)
            return nom, groupe, is_rapporteur
        elif acteur_ref:
            nom = nom_dict or acteur_ref
            groupe = groupe_natif or raw_signataire.get("groupe") or ""
            return nom, groupe, is_rapporteur
        elif groupe_natif:
            nom = nom_dict or libelle or ""
            return nom, groupe_natif, is_rapporteur
        elif libelle:
            # Repli sur le libellé texte
            return resolve_single_signataire(libelle)

    raw_str = html.unescape(str(raw_signataire or "")).strip()
    if not raw_str:
        return "", "", False

    if "gouvernement" in raw_str.lower():
        return "le Gouvernement", "GOUVERNEMENT", False

    if "rapporteur" in raw_str.lower() or "commission" in raw_str.lower():
        is_rapporteur = True

    # Si c'est un identifiant exact PA... (en exercice, sinon historique)
    dep = get_depute_info(raw_str)
    if dep:
        return dep.get("nom", raw_str), _groupe_de(dep), is_rapporteur

    clean_lower = raw_str.lower().strip()

    # 1. Correspondance exacte du nom complet (en exercice d'abord, puis historique)
    for base in (db, _load_historique_db()):
        for pa_id, dep in base.items():
            dep_nom = dep.get("nom", "").lower().strip()
            if dep_nom and dep_nom == clean_lower:
                return raw_str, _groupe_de(dep), is_rapporteur

    # 2. Correspondance du nom complet comme mot délimité (\b)
    for pa_id, dep in db.items():
        dep_nom = dep.get("nom", "").lower().strip()
        if dep_nom and re.search(rf"\b{re.escape(dep_nom)}\b", clean_lower):
            groupe = dep.get("groupe") or MAPPING_ORGANES_XVII.get(dep.get("organeRef", ""), "")
            return raw_str, groupe, is_rapporteur

    # 3. Correspondance par nom de famille (dernier token >= 4 lettres avec délimiteur \b)
    for pa_id, dep in db.items():
        dep_nom = dep.get("nom", "").lower().strip()
        parts = dep_nom.split()
        if parts:
            nom_famille = parts[-1]
            if len(nom_famille) >= 4 and re.search(rf"\b{re.escape(nom_famille)}\b", clean_lower):
                groupe = dep.get("groupe") or MAPPING_ORGANES_XVII.get(dep.get("organeRef", ""), "")
                return raw_str, groupe, is_rapporteur

    return raw_str, "", is_rapporteur


def resolve_signataires(signataires_raw: Any) -> dict[str, Any]:
    """
    Résout une structure de signataires (list, str ou dict) et retourne :
      - auteurs_formatte : chaîne lisible (ex: "Laurent Monnier (EPR), Léa Balage (EcoS)")
      - groupe_principal : acronyme du groupe du 1er signataire (ou "GOUVERNEMENT")
      - est_rapporteur : bool (True si rapporteur/commission détecté)
      - est_gouvernement : bool (True si Gouvernement détecté)
      - role : str ("Gouvernement", "Rapporteur" ou "Député")
    """
    if not signataires_raw:
        return {
            "auteurs_formatte": "",
            "groupe_principal": "",
            "est_rapporteur": False,
            "est_gouvernement": False,
            "role": "Député",
        }

    try:
        import html
        items_to_resolve: list[Any] = []
        global_rapporteur = False
        global_gouvernement = False
        groupe_principal = ""

        if isinstance(signataires_raw, dict):
            libelle = html.unescape(str(signataires_raw.get("libelle") or "")).strip()
            texte_libre = html.unescape(str(signataires_raw.get("texte") or "")).strip()

            if "gouvernement" in libelle.lower() or "gouvernement" in texte_libre.lower():
                global_gouvernement = True
                groupe_principal = "GOUVERNEMENT"

            if "rapporteur" in libelle.lower() or "rapporteur" in texte_libre.lower() or "commission" in texte_libre.lower():
                global_rapporteur = True

            # Priorité absolue au groupePolitiqueRef de l'auteur principal
            auteur_block = signataires_raw.get("auteur", {})
            if isinstance(auteur_block, dict):
                type_aut = str(auteur_block.get("typeAuteur") or "").lower()
                if "gouvernement" in type_aut:
                    global_gouvernement = True
                    groupe_principal = "GOUVERNEMENT"
                if "rapporteur" in type_aut:
                    global_rapporteur = True

                org_native = auteur_block.get("groupePolitiqueRef") or auteur_block.get("organeRef")
                if org_native and str(org_native) in MAPPING_ORGANES_XVII:
                    groupe_principal = MAPPING_ORGANES_XVII[str(org_native)]

                qualite = str(auteur_block.get("qualite") or "").lower()
                if "rapporteur" in qualite or "commission" in qualite:
                    global_rapporteur = True
                items_to_resolve.append(auteur_block)

            cosignataires = (
                signataires_raw.get("cosignataires")
                or signataires_raw.get("coSignataires")
                or signataires_raw.get("cosignatairesRefs")
                or []
            )
            if isinstance(cosignataires, list):
                items_to_resolve.extend(cosignataires[:5])
            elif isinstance(cosignataires, str):
                items_to_resolve.append(cosignataires)
        elif isinstance(signataires_raw, list):
            items_to_resolve.extend(signataires_raw)
        else:
            # Chaîne brute (éventuellement séparée par des virgules)
            str_val = html.unescape(str(signataires_raw)).strip()
            if "gouvernement" in str_val.lower():
                global_gouvernement = True
                groupe_principal = "GOUVERNEMENT"
            if "rapporteur" in str_val.lower() or "commission" in str_val.lower():
                global_rapporteur = True
            if "," in str_val:
                items_to_resolve.extend([part.strip() for part in str_val.split(",") if part.strip()])
            else:
                items_to_resolve.append(str_val)

        resolus = []

        for item in items_to_resolve:
            nom, grp, is_rap = resolve_single_signataire(item)
            if is_rap:
                global_rapporteur = True
            if grp == "GOUVERNEMENT" or nom == "le Gouvernement":
                global_gouvernement = True
            if not groupe_principal and grp:
                groupe_principal = grp

            if nom:
                if grp and grp != "GOUVERNEMENT":
                    resolus.append(f"{nom} ({grp})")
                else:
                    resolus.append(nom)

        if global_gouvernement:
            groupe_principal = "GOUVERNEMENT"
            if not resolus:
                resolus.append("le Gouvernement")

        auteurs_formatte = ", ".join(resolus) if resolus else (
            html.unescape(str(signataires_raw.get("libelle", ""))) if isinstance(signataires_raw, dict) and signataires_raw.get("libelle")
            else (str(signataires_raw) if not isinstance(signataires_raw, (dict, list)) else "")
        )

        role = "Gouvernement" if global_gouvernement else ("Rapporteur" if global_rapporteur else "Député")

        return {
            "auteurs_formatte": auteurs_formatte,
            "groupe_principal": groupe_principal,
            "est_rapporteur": global_rapporteur,
            "est_gouvernement": global_gouvernement,
            "role": role,
        }
    except Exception as exc:
        logger.warning(f"⚠️ Erreur inattendue resolve_signataires ({exc}). Mode dégradé sans crash.")
        return {
            "auteurs_formatte": str(signataires_raw) if signataires_raw and not isinstance(signataires_raw, (dict, list)) else "",
            "groupe_principal": "",
            "est_rapporteur": False,
            "est_gouvernement": False,
            "role": "Député",
        }
