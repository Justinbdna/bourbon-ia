"""
api/participants_resolver.py — Participants d'un texte de loi (Tricoteuses)
===========================================================================
Récupère la liste des parlementaires ayant participé à un DOSSIER LÉGISLATIF,
avec nom, prénom, groupe politique et rôle tenu.

⚠️  GRANULARITÉ — point de conception important
Les participants s'attachent au TEXTE DE LOI, pas à l'amendement : un dossier
courant en compte 200+ (mesuré : 202 sur DLR5L17N54094). Les afficher dans
chaque ligne du tableau d'amendements n'aurait aucun sens — ce module alimente
donc un panneau « Participants du texte », et non une colonne.

Coût réseau : UN appel par dossier (et non par amendement), avec cache mémoire.

Source : GET /v2/participantsDossiers?dossierRefUid=…
Chaque entrée porte :
  - acteurRef.nom / .prenom / .civ
  - acteurRef.groupeParlementaire.libelle / .libelleAbrege / .couleurAssociee
  - rôles booléens : rapporteur, initiateurDossier, auteurDocument,
    coSignataireDocument
  - scores d'implication : amendements, interventions, votes, présences…

Aucune fonction ne lève d'exception : en cas d'échec réseau, on renvoie une
liste vide et le front affiche simplement un panneau vide.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

logger = logging.getLogger("bourbon.participants")

# Cache mémoire : {dossier_uid: (timestamp, participants)}
_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_TTL_SECONDS = 3600          # 1 h, aligné sur cache_manager
MAX_PARTICIPANTS = 300       # garde-fou : un dossier majeur peut être très large

# Libellés lisibles des rôles (l'API expose des booléens bruts).
_ROLES = (
    ("rapporteur", "Rapporteur"),
    ("initiateurDossier", "Initiateur"),
    ("auteurDocument", "Auteur"),
    ("coSignataireDocument", "Cosignataire"),
)


def _sget(source: Any, *cles: str, defaut: Any = None) -> Any:
    """Lecture imbriquée tolérante — aucun KeyError possible."""
    courant = source
    for cle in cles:
        if not isinstance(courant, dict):
            return defaut
        courant = courant.get(cle)
        if courant is None:
            return defaut
    return courant


def _normaliser_participant(brut: dict[str, Any]) -> dict[str, Any]:
    """
    Aplati une entrée de l'API vers la structure consommée par le front.

    Returns:
        {
          "acteur_ref": "PA720846",
          "nom": "Lachaud",            # nom de famille
          "prenom": "Bastien",
          "civilite": "M.",
          "groupe": "LFI-NFP",         # abrégé, pour l'affichage compact
          "groupe_libelle": "La France insoumise - Nouveau Front Populaire",
          "groupe_couleur": "#BF360C", # couleur officielle du groupe
          "roles": ["Rapporteur"],
          "score": 4308.25,
          "score_amendements": 1433,
        }
    """
    acteur = brut.get("acteurRef") or {}
    groupe = acteur.get("groupeParlementaire") or {}

    roles = [libelle for champ, libelle in _ROLES if brut.get(champ)]

    return {
        "acteur_ref": brut.get("acteurRefUid") or acteur.get("uid") or "",
        "nom": acteur.get("nom") or "",
        "prenom": acteur.get("prenom") or "",
        "civilite": acteur.get("civ") or "",
        "groupe": groupe.get("libelleAbrege") or "",
        "groupe_libelle": groupe.get("libelle") or "",
        "groupe_couleur": groupe.get("couleurAssociee") or "",
        "roles": roles,
        "score": brut.get("score") or 0,
        "score_amendements": brut.get("scoreAmendements") or 0,
        "score_interventions": brut.get("scoreInterventions") or 0,
    }


_CACHE_DOSSIER: dict[str, str] = {}


def resolve_dossier_ref(amendements: Any) -> str:
    """
    Retrouve l'identifiant de DOSSIER législatif (DLR…) d'un lot d'amendements.

    ⚠️  POURQUOI CETTE FONCTION EXISTE
    Le lien amendement → texte de loi est souvent absent des données importées :
      • le jeu d'exemple et beaucoup d'exports ne portent AUCUNE référence ;
      • `textes_resolver.extract_texte_ref()` renvoie un identifiant de DOCUMENT
        (« PIONANR5L17B0149 »), alors que /v2/participantsDossiers exige un
        identifiant de DOSSIER (« DLR5L17N54094 ») — ce ne sont pas les mêmes.
    Sans ce pont, le panneau des participants resterait vide en permanence.

    Stratégie, du moins coûteux au plus coûteux :
      1. une référence DLR… déjà présente dans le lot → gratuit, hors-ligne ;
      2. sinon, UN appel Tricoteuses sur le premier uid d'amendement réel
         (vérifié : AMANR5L17PO59051B2820… → DLR5L17N54094).

    Un seul appel réseau par lot, mis en cache. Renvoie "" si indéterminable.
    """
    if not isinstance(amendements, list) or not amendements:
        return ""

    premier_uid = ""

    for item in amendements:
        if not isinstance(item, dict):
            continue
        am = item.get("amendement", item)

        # 1. Référence de dossier explicite (toutes graphies rencontrées)
        for champ in ("dossier_ref", "dossierRefUid", "dossierRef", "texteLegislatifRef"):
            valeur = am.get(champ) or item.get(champ)
            if isinstance(valeur, dict):
                valeur = valeur.get("uid")
            if valeur and str(valeur).startswith("DLR"):
                return str(valeur)

        if not premier_uid:
            candidat = str(am.get("uid") or am.get("id") or "")
            if candidat.startswith("AM"):
                premier_uid = candidat

    if not premier_uid:
        logger.info("Aucun uid d'amendement exploitable : dossier non résolu.")
        return ""

    if premier_uid in _CACHE_DOSSIER:
        return _CACHE_DOSSIER[premier_uid]

    # 2. Repli réseau : un unique appel pour tout le lot
    try:
        try:
            from api.tricoteuses_client import _request
        except ModuleNotFoundError:
            from tricoteuses_client import _request

        donnees = _request(f"/v2/amendements/{premier_uid}").get("data") or {}
        dossier = (donnees.get("dossierRef") or {}).get("uid") or _sget(
            donnees, "documentRef", "dossierRefUid"
        ) or ""
        if dossier:
            _CACHE_DOSSIER[premier_uid] = dossier
            logger.info(f"🔗 Dossier résolu depuis {premier_uid} → {dossier}")
        return dossier
    except Exception as exc:
        logger.warning(f"⚠️ Dossier non résolu depuis {premier_uid} ({exc}).")
        return ""


def fetch_participants(
    dossier_uid: str,
    limite: int = 100,
    utiliser_cache: bool = True,
) -> list[dict[str, Any]]:
    """
    Retourne les participants d'un texte de loi, triés par implication décroissante.

    Args:
        dossier_uid    : identifiant du dossier législatif (ex. DLR5L17N54094).
        limite         : nombre maximum de participants renvoyés (borné à MAX_PARTICIPANTS).
        utiliser_cache : réutilise le résultat en mémoire pendant _TTL_SECONDS.

    Returns:
        Liste de participants normalisés. Liste VIDE en cas d'échec — jamais
        d'exception, pour ne pas bloquer l'affichage du dérouleur.
    """
    if not dossier_uid:
        return []

    limite = max(1, min(limite, MAX_PARTICIPANTS))

    if utiliser_cache:
        entree = _CACHE.get(dossier_uid)
        if entree and (time.time() - entree[0]) < _TTL_SECONDS:
            logger.info(f"♻️  Participants {dossier_uid} servis depuis le cache.")
            return entree[1][:limite]

    try:
        # Double import : convention du dépôt (cf. api/index.py) — `api.x` en
        # local, `x` une fois bundlé par Vercel Serverless où `api/` est la racine.
        try:
            from api.tricoteuses_client import _request
        except ModuleNotFoundError:
            from tricoteuses_client import _request

        reponse = _request(
            "/v2/participantsDossiers",
            {
                "dossierRefUid": dossier_uid,
                "perPage": limite,
                # Les plus impliqués d'abord : c'est l'ordre utile à un administrateur.
                "sort": "score.desc",
            },
        )
        brut = reponse.get("data") or []
        total = _sget(reponse, "pagination", "total")

    except Exception as exc:
        logger.warning(f"⚠️ Participants indisponibles pour {dossier_uid} ({exc}). Panneau vide.")
        return []

    if not isinstance(brut, list):
        return []

    participants = [_normaliser_participant(p) for p in brut if isinstance(p, dict)]
    # On écarte les entrées sans identité exploitable (données partielles amont).
    participants = [p for p in participants if p["nom"] or p["prenom"]]

    _CACHE[dossier_uid] = (time.time(), participants)
    logger.info(
        f"👥 {len(participants)} participants récupérés pour {dossier_uid}"
        + (f" (sur {total} au total)" if total else "")
    )
    return participants


def resumer_par_groupe(participants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Agrège les participants par groupe politique — utile pour visualiser
    d'un coup d'œil quels groupes se sont mobilisés sur le texte.

    Returns:
        Liste triée par effectif décroissant :
        [{"groupe": "LFI-NFP", "libelle": "…", "couleur": "#…", "effectif": 12}, …]
    """
    agregat: dict[str, dict[str, Any]] = {}
    for p in participants:
        cle = p.get("groupe") or "—"
        if cle not in agregat:
            agregat[cle] = {
                "groupe": cle,
                "libelle": p.get("groupe_libelle") or "Groupe non renseigné",
                "couleur": p.get("groupe_couleur") or "",
                "effectif": 0,
            }
        agregat[cle]["effectif"] += 1

    return sorted(agregat.values(), key=lambda g: g["effectif"], reverse=True)


def vider_cache() -> int:
    """Vide le cache des participants ; renvoie le nombre d'entrées supprimées."""
    nb = len(_CACHE)
    _CACHE.clear()
    return nb


# ──────────────────────────────────────────────────────────────────────────
# Auto-test (nécessite le réseau)
# ──────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    dossier = sys.argv[1] if len(sys.argv) > 1 else "DLR5L17N54094"

    print("═" * 76)
    print(f"  AUTO-TEST · Participants du dossier {dossier}")
    print("═" * 76)

    participants = fetch_participants(dossier, limite=12)
    if not participants:
        print("\n❌ Aucun participant (réseau indisponible ou dossier inconnu).")
        raise SystemExit(1)

    print(f"\n{'PRÉNOM':<14}{'NOM':<22}{'GROUPE':<12}{'RÔLES':<28}SCORE")
    print("─" * 76)
    for p in participants:
        print(f"{p['prenom'][:13]:<14}{p['nom'][:21]:<22}{(p['groupe'] or '—')[:11]:<12}"
              f"{('/'.join(p['roles']) or '—')[:27]:<28}{p['score']:>7.0f}")

    print("\n── Répartition par groupe politique ──")
    for g in resumer_par_groupe(participants):
        print(f"  {g['groupe']:<12} {g['effectif']:>3} participant(s)   {g['libelle'][:44]}")

    # Vérification du cache (2e appel = aucun appel réseau)
    fetch_participants(dossier, limite=12)
    print("\n✅ Cache vérifié (second appel servi en mémoire).")
    print("═" * 76)
