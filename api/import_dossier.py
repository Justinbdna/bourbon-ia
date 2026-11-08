"""
api/import_dossier.py — Import direct des amendements d'un dossier législatif
=============================================================================
Remplace le téléchargement manuel d'un fichier JSON : l'utilisateur cherche un
dossier législatif (XVIIe législature), choisit une liasse (étape de lecture à
l'Assemblée) et Bourbon.IA récupère ses amendements via l'API Tricoteuses, qui
redistribue les données ouvertes de l'Assemblée (« Amendements par dossier
législatif », data.assemblee-nationale.fr).

Les amendements sont convertis au FORMAT BRUT DE L'ASSEMBLÉE (uid,
identification, pointeurFragmentTexte, signataires, corps…) : le reste de la
chaîne (normalisation, tri déterministe, IA) les traite exactement comme un
fichier JSON importé.

Limite connue : l'API ne fournit que l'auteur principal (pas la liste des
cosignataires, seulement leur nombre).

Désactivable (mode air-gapped) avec BOURBON_TEXTES_DISTANTS=0, comme la
récupération du texte de loi.
"""

from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

try:
    from api.tricoteuses_client import MAX_PER_PAGE, TricoteusesError, _request
except ModuleNotFoundError:
    from tricoteuses_client import MAX_PER_PAGE, TricoteusesError, _request

LEGISLATURE = 17

# Le schéma de requête de /api/v2/mecanique accepte 2 000 amendements au plus.
MAX_AMENDEMENTS = 2000

# Étapes de lecture à l'Assemblée (codeEtape), dans l'ordre de la procédure.
ETAPES_AN: dict[str, str] = {
    "AN1-COM": "1re lecture — Commission",
    "AN1-DEBATS": "1re lecture — Séance publique",
    "AN2-COM": "2e lecture — Commission",
    "AN2-DEBATS": "2e lecture — Séance publique",
    "ANNLEC-COM": "Nouvelle lecture — Commission",
    "ANNLEC-DEBATS": "Nouvelle lecture — Séance publique",
    "ANLUNI-COM": "Lecture unique — Commission",
    "ANLUNI-DEBATS": "Lecture unique — Séance publique",
    "CMP-DEBATS": "Commission mixte paritaire — Séance publique",
}

_DOSSIER_UID_RE = re.compile(r"^DLR5L\d{2}N\d+$")


class ImportIndisponible(Exception):
    """Import distant désactivé ou API injoignable (message lisible par l'utilisateur)."""


def import_distant_active() -> bool:
    return os.getenv("BOURBON_TEXTES_DISTANTS", "1").strip().lower() not in ("0", "false", "non", "off")


def _verifier_disponible() -> None:
    if not import_distant_active():
        raise ImportIndisponible(
            "Import en ligne désactivé (mode hors-ligne) : importez un fichier JSON."
        )


def dossier_uid_valide(uid: str) -> bool:
    return bool(_DOSSIER_UID_RE.match(uid or ""))


def _appel(path: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        return _request(path, params)
    except TricoteusesError as exc:
        raise ImportIndisponible(
            "Données de l'Assemblée momentanément injoignables (API Tricoteuses). Réessayez plus tard."
        ) from exc


# ──────────────────────────────────────────────────────────────────────────
# 1. Recherche de dossiers
# ──────────────────────────────────────────────────────────────────────────
def rechercher_dossiers(recherche: str, limite: int = 15) -> list[dict[str, Any]]:
    """Dossiers législatifs de la XVIIe législature dont le titre correspond, les plus récents d'abord."""
    _verifier_disponible()
    reponse = _appel(
        "/v2/dossiers",
        {
            "legislature": LEGISLATURE,
            "search": recherche.strip() or None,
            "sort": "dateDernierActe.desc",
            "perPage": max(1, min(limite, 50)),
        },
    )
    return [
        {
            "uid": d.get("uid", ""),
            "titre": d.get("titre", ""),
            "type": d.get("typeInitiative", ""),
            "statut": d.get("statut", ""),
            "date_dernier_acte": (d.get("dateDernierActe") or "")[:10],
        }
        for d in (reponse.get("data") or [])
        if isinstance(d, dict) and d.get("uid")
    ]


# ──────────────────────────────────────────────────────────────────────────
# 2. Liasses d'un dossier (une par étape de lecture à l'Assemblée)
# ──────────────────────────────────────────────────────────────────────────
def lister_liasses(dossier_uid: str) -> list[dict[str, Any]]:
    """Étapes du dossier ayant des amendements à l'Assemblée, avec leur nombre."""
    _verifier_disponible()

    def compter(code: str) -> dict[str, Any]:
        reponse = _appel(
            "/v2/amendements",
            {"dossierRefUid": dossier_uid, "codeEtape": code, "chambre": "AN", "perPage": 1},
        )
        return {"etape": code, "libelle": ETAPES_AN[code], "nb": reponse["pagination"].get("total") or 0}

    with ThreadPoolExecutor(max_workers=len(ETAPES_AN)) as pool:
        liasses = list(pool.map(compter, ETAPES_AN))
    return [l for l in liasses if l["nb"] > 0]


# ──────────────────────────────────────────────────────────────────────────
# 3. Amendements d'une liasse, au format brut de l'Assemblée
# ──────────────────────────────────────────────────────────────────────────
def tricoteuses_vers_format_an(a: dict[str, Any]) -> dict[str, Any]:
    """Convertit un amendement de l'API Tricoteuses au format JSON brut de l'Assemblée."""
    document = a.get("documentRef") or {}
    groupe = a.get("groupePolitiqueRef") or {}
    # En liste, l'API laisse `acteurRefUid` vide et ne renseigne que l'objet `acteurRef`.
    auteur_uid = a.get("acteurRefUid") or (a.get("acteurRef") or {}).get("uid") or ""
    # Le premier amendement d'une discussion d'identiques porte l'identifiant
    # de discussion sans être marqué `estIdentique`.
    id_discussion = a.get("idDiscussionIdentique")
    return {
        "uid": a.get("uid", ""),
        "identification": {"numeroLong": a.get("numeroLong") or str(a.get("numeroOrdreDepot") or "")},
        "pointeurFragmentTexte": {
            "division": {
                "titre": a.get("divisionTitre") or "",
                "articleDesignationCourte": a.get("divisionArticleDesignationCourte") or "",
                "articleDesignation": a.get("divisionArticleDesignation") or "",
            },
            "alinea": {"alineaDesignation": a.get("alineaDesignation") or ""},
        },
        "signataires": {
            "auteur": {
                "typeAuteur": a.get("typeAuteur") or "",
                "acteurRef": auteur_uid,
                "groupePolitiqueRef": groupe.get("uid") or "",
            },
            "cosignatairesRefs": [],
        },
        "corps": {
            "contenuAuteur": {
                "dispositif": a.get("dispositifHtml") or a.get("dispositif") or "",
                "exposeSommaire": a.get("exposeSommaireHtml") or a.get("exposeSommaire") or "",
            },
            "cartoucheInformatif": a.get("cartoucheInformatif") or "",
        },
        "cycleDeVie": {"etatChronologique": {"mention": a.get("etatLibelle") or ""}},
        "sort": a.get("sortAmendement") or "",
        "texteLegislatifRef": document.get("uid") or "",
        "discussionIdentique": {"idDiscussion": str(id_discussion)} if id_discussion else None,
        "idDiscussionIdentique": str(id_discussion) if id_discussion else None,
        "estIdentique": bool(a.get("estIdentique")),
        "amendementParentRef": a.get("amendementParentRefUid") or None,
        "triAmendement": a.get("triAmendement") or "",
    }


def amendements_de_liasse(dossier_uid: str, etape: str) -> dict[str, Any]:
    """
    Amendements d'une étape du dossier, dans l'ordre de la liasse (triAmendement).
    Au-delà de MAX_AMENDEMENTS, la liste est tronquée et `tronque` vaut True.
    """
    _verifier_disponible()
    filtres = {"dossierRefUid": dossier_uid, "codeEtape": etape, "chambre": "AN", "sort": "triAmendement.asc"}

    premiere = _appel("/v2/amendements", {**filtres, "page": 1, "perPage": MAX_PER_PAGE})
    total = premiere["pagination"].get("total") or 0
    pages = min(-(-min(total, MAX_AMENDEMENTS) // MAX_PER_PAGE), MAX_AMENDEMENTS // MAX_PER_PAGE)

    bruts = list(premiere.get("data") or [])
    if pages > 1:
        with ThreadPoolExecutor(max_workers=pages - 1) as pool:
            suivantes = pool.map(
                lambda p: _appel("/v2/amendements", {**filtres, "page": p, "perPage": MAX_PER_PAGE}),
                range(2, pages + 1),
            )
            for reponse in suivantes:
                bruts.extend(reponse.get("data") or [])

    bruts = [a for a in bruts if isinstance(a, dict)][:MAX_AMENDEMENTS]
    return {
        "amendements": [tricoteuses_vers_format_an(a) for a in bruts],
        "total": total,
        "tronque": total > len(bruts),
    }
