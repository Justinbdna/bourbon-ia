"""
api/tricoteuses_client.py — Connecteur REST vers l'API « Les Tricoteuses »
==========================================================================
Chantier V2 : récupération du CONTEXTE ENRICHI (Acteurs + Dossiers législatifs)
destiné à fiabiliser le classement de l'IA.

⚠️  MODULE VOLONTAIREMENT ISOLÉ
Ce fichier n'est branché NI dans `api/index.py` NI dans le front (`App.jsx`).
Il ne contient aucune logique métier (pas de mapping vers notre schéma plat,
pas de validation Pydantic) : uniquement la couche de connexion HTTP.
L'intégration et le mapping feront l'objet d'un chantier distinct.

Source (open source, AGPL) :
    https://git.tricoteuses.fr/logiciels/tricoteuses-api-parlement

Endpoints REST v2 repérés dans `src/routes/v2/index.ts` du dépôt amont
(le routeur v2 est monté sur le préfixe `/v2` dans `src/server.ts:144`) :

    GET /v2/amendements          → liste paginée des amendements
    GET /v2/amendements/{uid}    → un amendement
    GET /v2/acteurs              → liste paginée des acteurs / députés
                                   (équivalent du fichier AMO 30 de l'AN)
    GET /v2/acteurs/{uid}        → un acteur
    GET /v2/dossiers             → liste paginée des dossiers législatifs
    GET /v2/dossiers/{uid}       → un dossier législatif (contexte de la loi)

Conventions de l'API amont :
  - Pagination par `page` (défaut 1) et `perPage` (défaut 10)
    → cf. `src/schemas/paginationSchemas.ts`
  - Le corps de réponse est un objet `{ "data": [...] }`
  - Le total est renvoyé dans les EN-TÊTES : `total`, `total-page`, `per-page`

Usage (module autonome, exécutable directement) :
    python3 api/tricoteuses_client.py
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger("bourbon.tricoteuses")

# ──────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────
# Instance publique de production. Surchargeable via .env pour pointer vers
# l'instance de recette (`parlement-staging.tricoteuses.fr`) ou une instance
# auto-hébergée — indispensable pour le mode souverain de Bourbon.IA.
BASE_URL: str = os.environ.get("TRICOTEUSES_API_URL", "https://parlement.tricoteuses.fr").rstrip("/")

# L'API amont met ses réponses en cache 10 min ; un timeout généreux évite
# les faux négatifs sur les gros volumes (184 000+ amendements indexés).
DEFAULT_TIMEOUT: float = float(os.environ.get("TRICOTEUSES_TIMEOUT", "30"))

# Garde-fou : l'API accepte de grandes valeurs, mais on borne pour éviter
# de saturer la mémoire d'une fonction serverless.
MAX_PER_PAGE: int = 500


# ──────────────────────────────────────────────────────────────────────────
# Erreurs
# ──────────────────────────────────────────────────────────────────────────
class TricoteusesError(Exception):
    """
    Erreur de communication avec l'API Tricoteuses.

    Attributs :
        status_code : code HTTP si la réponse a été reçue, sinon None
                      (None = panne réseau / DNS / timeout).
    """

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code

    def __str__(self) -> str:
        base = super().__str__()
        return f"[HTTP {self.status_code}] {base}" if self.status_code else base


# ──────────────────────────────────────────────────────────────────────────
# Couche HTTP interne
# ──────────────────────────────────────────────────────────────────────────
def _clean_params(params: dict[str, Any]) -> dict[str, Any]:
    """Retire les paramètres vides pour ne pas polluer l'URL (`?uid=&page=1`)."""
    return {k: v for k, v in params.items() if v is not None and v != ""}


def _request(path: str, params: Optional[dict[str, Any]] = None, timeout: Optional[float] = None) -> dict[str, Any]:
    """
    Exécute un GET sur l'API et normalise le retour.

    Returns:
        {
          "data": <list|dict>,     # charge utile renvoyée par l'API
          "pagination": {          # extrait des en-têtes HTTP
              "total": int|None,
              "total_pages": int|None,
              "per_page": int|None,
          },
        }

    Raises:
        TricoteusesError : 404 (ressource inconnue), 4xx, 5xx, ou panne réseau.
    """
    url = f"{BASE_URL}{path}"
    params = _clean_params(params or {})

    try:
        with httpx.Client(timeout=timeout or DEFAULT_TIMEOUT, follow_redirects=True) as client:
            response = client.get(url, params=params, headers={"Accept": "application/json"})

        # ── Gestion explicite des statuts utiles au diagnostic ──
        if response.status_code == 404:
            raise TricoteusesError(f"Ressource introuvable : {url}", 404)
        if response.status_code == 429:
            raise TricoteusesError("Quota de requêtes dépassé sur l'API Tricoteuses.", 429)
        if 500 <= response.status_code < 600:
            raise TricoteusesError(f"Erreur serveur de l'API Tricoteuses ({url}).", response.status_code)
        if response.status_code >= 400:
            raise TricoteusesError(f"Requête refusée par l'API Tricoteuses : {response.text[:200]}", response.status_code)

        try:
            payload = response.json()
        except ValueError as exc:  # réponse non-JSON (page d'erreur HTML, proxy…)
            raise TricoteusesError(f"Réponse non-JSON reçue de {url}.") from exc

    except TricoteusesError:
        raise  # déjà qualifiée, on ne la masque pas
    except httpx.TimeoutException as exc:
        raise TricoteusesError(f"Délai dépassé ({timeout or DEFAULT_TIMEOUT}s) sur {url}.") from exc
    except httpx.RequestError as exc:
        # DNS, TLS, connexion refusée, réseau coupé…
        raise TricoteusesError(f"Connexion impossible à l'API Tricoteuses : {exc}") from exc

    def _header_int(name: str) -> Optional[int]:
        raw = response.headers.get(name)
        try:
            return int(raw) if raw is not None else None
        except (TypeError, ValueError):
            return None

    # L'API encapsule les listes dans `{"data": [...]}` ; les vues unitaires
    # peuvent renvoyer l'objet directement. On homogénéise ici.
    data = payload.get("data", payload) if isinstance(payload, dict) else payload

    return {
        "data": data,
        "pagination": {
            "total": _header_int("total"),
            "total_pages": _header_int("total-page"),
            "per_page": _header_int("per-page"),
        },
    }


# ──────────────────────────────────────────────────────────────────────────
# 1. AMENDEMENTS
# ──────────────────────────────────────────────────────────────────────────
def fetch_amendements(
    uid: Optional[str] = None,
    dossier_uid: Optional[str] = None,
    legislature: Optional[int] = None,
    page: int = 1,
    per_page: int = 100,
    sort: Optional[str] = None,
    timeout: Optional[float] = None,
    **filtres: Any,
) -> dict[str, Any]:
    """
    Récupère des amendements.

    Args:
        uid         : si fourni, récupère CET amendement (GET /v2/amendements/{uid}).
        dossier_uid : filtre sur le dossier législatif (`dossierRefUid` en amont).
        legislature : numéro de législature (14 à 17 côté amont).
        page        : page à récupérer (1-indexée).
        per_page    : éléments par page (borné à MAX_PER_PAGE).
        sort        : tri amont au format `"champ.direction"`, plusieurs tris
                      séparés par des virgules (cf. `buildSortSchema()` amont).
                      Direction obligatoire : `asc` ou `desc`.
                      Ex. `"triAmendement.asc"` ou
                          `"divisionArticleDesignation.asc,numeroOrdreDepot.asc"`.
                      Champs autorisés : dateDepot, datePublication, dateSort,
                      nombreCoSignataires, triAmendement, numeroOrdreDepot,
                      divisionArticleDesignation.
                      ⚠️ Un simple nom de champ sans direction renvoie un HTTP 400.
        **filtres   : tout autre filtre supporté en amont, passé tel quel
                      (ex. `estIdentique=True`, `acteurRefUid="PA..."`,
                      `divisionArticleDesignation="Article 5"`).

    Returns:
        dict — voir `_request()`.

    Raises:
        TricoteusesError
    """
    if uid:
        return _request(f"/v2/amendements/{uid}", timeout=timeout)

    params: dict[str, Any] = {
        "page": page,
        "perPage": min(per_page, MAX_PER_PAGE),
        "dossierRefUid": dossier_uid,
        "legislature": legislature,
        "sort": sort,
        **filtres,
    }
    return _request("/v2/amendements", params, timeout=timeout)


# ──────────────────────────────────────────────────────────────────────────
# 2. ACTEURS / DÉPUTÉS  (équivalent AMO 30)
# ──────────────────────────────────────────────────────────────────────────
def fetch_acteurs(
    uid: Optional[str] = None,
    page: int = 1,
    per_page: int = 100,
    timeout: Optional[float] = None,
    **filtres: Any,
) -> dict[str, Any]:
    """
    Récupère les acteurs (députés, sénateurs, membres du Gouvernement).
    Équivalent structuré du fichier AMO 30 diffusé par l'Assemblée nationale.

    Intérêt pour Bourbon.IA : distinguer un DOUBLON (même auteur) d'un
    amendement IDENTIQUE (auteurs différents) repose sur une identification
    fiable de l'auteur — c'est précisément ce que cet endpoint apporte.

    Args:
        uid       : si fourni, récupère CET acteur (GET /v2/acteurs/{uid}).
        page      : page à récupérer (1-indexée).
        per_page  : éléments par page (borné à MAX_PER_PAGE).
        **filtres : filtres supplémentaires supportés en amont.

    Returns:
        dict — voir `_request()`.

    Raises:
        TricoteusesError
    """
    if uid:
        return _request(f"/v2/acteurs/{uid}", timeout=timeout)

    params: dict[str, Any] = {
        "page": page,
        "perPage": min(per_page, MAX_PER_PAGE),
        **filtres,
    }
    return _request("/v2/acteurs", params, timeout=timeout)


# ──────────────────────────────────────────────────────────────────────────
# 3. DOSSIERS LÉGISLATIFS  (contexte de la loi)
# ──────────────────────────────────────────────────────────────────────────
def fetch_dossier_legislatif(
    uid: Optional[str] = None,
    page: int = 1,
    per_page: int = 100,
    timeout: Optional[float] = None,
    **filtres: Any,
) -> dict[str, Any]:
    """
    Récupère un dossier législatif (ou la liste paginée si `uid` est omis).

    Intérêt pour Bourbon.IA : le dossier porte le contexte du texte examiné
    (intitulé, étapes législatives). Il alimentera l'en-tête du dérouleur et
    permettra de restituer l'ORDRE RÉEL des articles du texte — l'ordre
    séquentiel prime sur la hiérarchie des points d'impact.

    Args:
        uid       : UID du dossier (GET /v2/dossiers/{uid}).
        page      : page à récupérer (1-indexée), si listing.
        per_page  : éléments par page (borné à MAX_PER_PAGE).
        **filtres : filtres supplémentaires supportés en amont.

    Returns:
        dict — voir `_request()`.

    Raises:
        TricoteusesError
    """
    if uid:
        return _request(f"/v2/dossiers/{uid}", timeout=timeout)

    params: dict[str, Any] = {
        "page": page,
        "perPage": min(per_page, MAX_PER_PAGE),
        **filtres,
    }
    return _request("/v2/dossiers", params, timeout=timeout)


# ──────────────────────────────────────────────────────────────────────────
# Alias conformes à la nomenclature de la mission V2
# (le reste du module suit la convention snake_case du backend existant)
# ──────────────────────────────────────────────────────────────────────────
fetchAmendements = fetch_amendements
fetchActeurs = fetch_acteurs
fetchDossierLegislatif = fetch_dossier_legislatif


# ──────────────────────────────────────────────────────────────────────────
# Test de connexion autonome (aucun impact sur l'application)
# ──────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print(f"Cible : {BASE_URL}\n")

    for libelle, appel in (
        ("Amendements", lambda: fetch_amendements(per_page=1)),
        ("Acteurs (AMO 30)", lambda: fetch_acteurs(per_page=1)),
        ("Dossiers législatifs", lambda: fetch_dossier_legislatif(per_page=1)),
    ):
        try:
            resultat = appel()
            total = resultat["pagination"]["total"]
            data = resultat["data"]
            nb = len(data) if isinstance(data, list) else 1
            print(f"✅ {libelle:<22} — {nb} élément(s) reçu(s), total disponible : {total}")
        except TricoteusesError as err:
            print(f"❌ {libelle:<22} — {err}")
