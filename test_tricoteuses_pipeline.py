#!/usr/bin/env python3
"""
test_tricoteuses_pipeline.py — Crash-test du pipeline d'enrichissement V2
=========================================================================
Valide la chaîne complète de récupération du CONTEXTE ENRICHI en 3 appels
successifs à l'API « Les Tricoteuses », via `api/tricoteuses_client.py` :

    1. AMENDEMENT  → GET /v2/amendements/{uid}
    2. AUTEUR      → GET /v2/acteurs/{uid}        (équivalent AMO 30)
    3. DOSSIER     → GET /v2/dossiers/{uid}       (contexte de la loi)

… puis fusionne le tout dans un dictionnaire `amendement_enrichi`.

Script de VALIDATION uniquement : il n'est branché ni au backend ni au front.

Usage :
    python3 test_tricoteuses_pipeline.py              # sélection auto d'un amendement AN
    python3 test_tricoteuses_pipeline.py <uid>        # cibler un amendement précis

Code de sortie : 0 si le pipeline est valide, 1 sinon (exploitable en CI).

──────────────────────────────────────────────────────────────────────────────
⚠️  ÉCARTS CONSTATÉS ENTRE LE SCHÉMA ATTENDU ET L'API RÉELLE
Tricoteuses APLATIT le JSON brut de l'Assemblée. Les chemins ci-dessous ont
été vérifiés en direct contre parlement.tricoteuses.fr :

  • `signataires.auteur.acteurRef`  → N'EXISTE PAS.
    L'auteur est exposé à plat : `acteurRefUid` (str) et `acteurRef` (objet
    partiel : uid, nom, prenom, civ, urlImage).

  • `auteur.trigramme`              → AUCUN équivalent amont.
    Le champ le plus proche est `groupeParlementaire.libelleAbrege`
    (abrégé du groupe). Renseigné ici sous `trigramme` pour stabilité du
    contrat, mais la provenance est tracée dans `_meta.mappings`.

  • `auteur.groupePolitiqueRef`     → n'existe que sur l'AMENDEMENT.
    Sur l'ACTEUR, le champ s'appelle `groupeParlementaire`.

  • `dossier.procedure`             → N'EXISTE PAS.
    Mappé depuis `libelleProcedure`, complété par `procedureAcceleree`
    et `typeInitiative`.

  • `idDiscussionIdentique`         → présent sur la vue LISTE, absent de la
    vue unitaire (SHOW). Récupéré depuis la liste quand disponible.
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import sys
from typing import Any, Optional

from api.tricoteuses_client import (
    BASE_URL,
    TricoteusesError,
    fetch_acteurs,
    fetch_amendements,
    fetch_dossier_legislatif,
)


# ──────────────────────────────────────────────────────────────────────────
# Utilitaires de lecture défensive (aucun KeyError possible)
# ──────────────────────────────────────────────────────────────────────────
def sget(source: Any, *cles: str, defaut: Any = None) -> Any:
    """
    Lecture imbriquée tolérante : sget(obj, "acteurRef", "uid").
    Renvoie `defaut` dès qu'un maillon est absent ou n'est pas un dict.
    """
    courant = source
    for cle in cles:
        if not isinstance(courant, dict):
            return defaut
        courant = courant.get(cle)
        if courant is None:
            return defaut
    return courant


def log(etape: str, message: str) -> None:
    print(f"[{etape}] {message}")


# ──────────────────────────────────────────────────────────────────────────
# Étape 0 — Sélection d'un amendement exploitable
# ──────────────────────────────────────────────────────────────────────────
def selectionner_amendement(uid_force: Optional[str] = None) -> tuple[str, Optional[int]]:
    """
    Détermine l'UID de l'amendement à tester.

    Sans UID imposé, on cherche un amendement de l'Assemblée nationale
    (chambre=AN, législature 17) disposant À LA FOIS d'un auteur et d'un
    dossier rattaché — sinon le test des étapes 2 et 3 serait vide de sens.
    On privilégie un amendement `estIdentique=True`, cas le plus utile au
    classement de Bourbon.IA.

    Returns:
        (uid, id_discussion_identique) — le second n'existe que sur la vue liste.
    """
    if uid_force:
        log("0/4", f"UID imposé en argument : {uid_force}")
        return uid_force, None

    # 1re tentative : amendements identiques (cas métier le plus riche)
    # 2e tentative : n'importe quel amendement AN
    tentatives = (
        {"chambre": "AN", "legislature": 17, "estIdentique": True},
        {"chambre": "AN", "legislature": 17},
    )

    for filtres in tentatives:
        lot = fetch_amendements(per_page=10, **filtres)["data"]
        exploitables = [
            a for a in lot
            if sget(a, "acteurRef", "uid") and sget(a, "dossierRef", "uid")
        ]
        if exploitables:
            choisi = exploitables[0]
            log("0/4", f"Amendement retenu : {choisi['uid']} "
                       f"({choisi.get('numeroLong')} — {choisi.get('divisionArticleDesignationCourte')})")
            return choisi["uid"], choisi.get("idDiscussionIdentique")

    raise TricoteusesError("Aucun amendement AN exploitable (auteur + dossier) trouvé.")


# ──────────────────────────────────────────────────────────────────────────
# Pipeline d'enrichissement
# ──────────────────────────────────────────────────────────────────────────
def construire_amendement_enrichi(uid_force: Optional[str] = None) -> dict[str, Any]:
    """
    Exécute les 3 appels et renvoie le dictionnaire `amendement_enrichi`.

    Raises:
        TricoteusesError : si l'un des appels échoue (réseau, 404, 5xx…).
    """
    uid_amendement, id_discussion_liste = selectionner_amendement(uid_force)

    # ── 1/4 · AMENDEMENT ────────────────────────────────────────────────
    amendement = fetch_amendements(uid=uid_amendement)["data"]
    log("1/4", f"Amendement récupéré — {amendement.get('numeroLong')} "
               f"({len(amendement.get('dispositif') or '')} car. de dispositif)")

    # ── 2/4 · AUTEUR (AMO 30) ───────────────────────────────────────────
    # Chemin réel : `acteurRefUid`, avec repli sur l'objet partiel `acteurRef.uid`.
    uid_auteur = amendement.get("acteurRefUid") or sget(amendement, "acteurRef", "uid")
    auteur: dict[str, Any] = {}
    if uid_auteur:
        auteur = fetch_acteurs(uid=uid_auteur)["data"]
        log("2/4", f"Auteur récupéré — {uid_auteur} : "
                   f"{auteur.get('prenom')} {auteur.get('nom')}")
    else:
        # Cas légitime : amendement du Gouvernement ou d'une commission.
        log("2/4", "⚠️  Aucun auteur individuel (amendement Gouvernement/commission) "
                   "— section `auteur` laissée vide.")

    # ── 3/4 · DOSSIER LÉGISLATIF ────────────────────────────────────────
    uid_dossier = (
        sget(amendement, "dossierRef", "uid")
        or sget(amendement, "documentRef", "dossierRefUid")
    )
    dossier: dict[str, Any] = {}
    if uid_dossier:
        dossier = fetch_dossier_legislatif(uid=uid_dossier)["data"]
        log("3/4", f"Dossier récupéré — {uid_dossier} : "
                   f"{(dossier.get('titre') or '')[:60]}…")
    else:
        log("3/4", "⚠️  Aucun dossier rattaché — section `dossier` laissée vide.")

    # ── 4/4 · FUSION ────────────────────────────────────────────────────
    # `idDiscussionIdentique` n'est pas exposé par la vue unitaire :
    # on retombe sur la valeur captée à l'étape 0 (vue liste).
    id_discussion = amendement.get("idDiscussionIdentique", id_discussion_liste)

    amendement_enrichi: dict[str, Any] = {
        "amendement": {
            "uid": amendement.get("uid"),
            "numeroLong": amendement.get("numeroLong"),
            "dispositif": amendement.get("dispositif"),
            "exposeSommaire": amendement.get("exposeSommaire"),
            "estIdentique": amendement.get("estIdentique"),
            "idDiscussionIdentique": id_discussion,
            # Contexte de classement (bonus utile au moteur déterministe)
            "divisionArticleDesignation": amendement.get("divisionArticleDesignation"),
            "triAmendement": amendement.get("triAmendement"),
        },
        "auteur": {
            "uid": auteur.get("uid") or uid_auteur,
            "nom": auteur.get("nom") or sget(amendement, "acteurRef", "nom"),
            "prenom": auteur.get("prenom") or sget(amendement, "acteurRef", "prenom"),
            # Pas de `trigramme` en amont → abrégé du groupe parlementaire.
            "trigramme": sget(auteur, "groupeParlementaire", "libelleAbrege"),
            # Sur l'acteur le champ s'appelle `groupeParlementaire` ; on retombe
            # sur `groupePolitiqueRef` porté par l'amendement lui-même.
            "groupePolitiqueRef": (
                auteur.get("groupeParlementaire")
                or amendement.get("groupePolitiqueRef")
            ),
        },
        "dossier": {
            "uid": dossier.get("uid") or uid_dossier,
            "titre": dossier.get("titre") or sget(amendement, "dossierRef", "titre"),
            # Pas de `procedure` en amont → `libelleProcedure` + compléments.
            "procedure": dossier.get("libelleProcedure"),
            "procedureAcceleree": dossier.get("procedureAcceleree"),
            "typeInitiative": dossier.get("typeInitiative"),
        },
        # Traçabilité : aucun champ inventé, chaque écart est documenté.
        "_meta": {
            "source": BASE_URL,
            "appels_api": 3,
            "mappings": {
                "auteur.uid": "amendement.acteurRefUid (et non signataires.auteur.acteurRef)",
                "auteur.trigramme": "acteur.groupeParlementaire.libelleAbrege (aucun trigramme en amont)",
                "auteur.groupePolitiqueRef": "acteur.groupeParlementaire (repli : amendement.groupePolitiqueRef)",
                "dossier.procedure": "dossier.libelleProcedure (aucun champ 'procedure' en amont)",
                "amendement.idDiscussionIdentique": "vue LISTE uniquement (absent de la vue unitaire)",
            },
        },
    }

    return amendement_enrichi


# ──────────────────────────────────────────────────────────────────────────
# Validation de structure
# ──────────────────────────────────────────────────────────────────────────
STRUCTURE_ATTENDUE = {
    "amendement": ["uid", "numeroLong", "dispositif", "exposeSommaire",
                   "estIdentique", "idDiscussionIdentique"],
    "auteur": ["uid", "nom", "prenom", "trigramme", "groupePolitiqueRef"],
    "dossier": ["uid", "titre", "procedure"],
}


def valider(enrichi: dict[str, Any]) -> bool:
    """Vérifie la présence des clés requises et signale les valeurs nulles."""
    manquantes: list[str] = []
    nulles: list[str] = []

    for section, cles in STRUCTURE_ATTENDUE.items():
        if section not in enrichi:
            manquantes.append(section)
            continue
        for cle in cles:
            if cle not in enrichi[section]:
                manquantes.append(f"{section}.{cle}")
            elif enrichi[section][cle] is None:
                nulles.append(f"{section}.{cle}")

    print("\n" + "─" * 62)
    if manquantes:
        print(f"❌ Clés ABSENTES du contrat : {', '.join(manquantes)}")
    else:
        print("✅ Structure conforme — toutes les clés requises sont présentes.")

    if nulles:
        # Une valeur nulle n'est pas un échec : elle peut être légitime
        # (amendement du Gouvernement, groupe non renseigné…).
        print(f"ℹ️  Champs présents mais nuls (à surveiller) : {', '.join(nulles)}")

    return not manquantes


# ──────────────────────────────────────────────────────────────────────────
# Point d'entrée
# ──────────────────────────────────────────────────────────────────────────
def main() -> int:
    uid_force = sys.argv[1] if len(sys.argv) > 1 else None

    print("═" * 62)
    print("  CRASH-TEST · Pipeline d'enrichissement Tricoteuses (V2)")
    print(f"  Cible : {BASE_URL}")
    print("═" * 62)

    try:
        amendement_enrichi = construire_amendement_enrichi(uid_force)
    except TricoteusesError as err:
        print(f"\n❌ ÉCHEC — appel API : {err}", file=sys.stderr)
        return 1
    except Exception as err:  # filet de sécurité : le test ne doit jamais crasher brutalement
        print(f"\n❌ ÉCHEC — erreur inattendue ({type(err).__name__}) : {err}", file=sys.stderr)
        return 1

    print("\n── RÉSULTAT FUSIONNÉ (amendement_enrichi) ──")
    print(json.dumps(amendement_enrichi, indent=2, ensure_ascii=False))

    ok = valider(amendement_enrichi)
    print("─" * 62)
    print("🎉 Pipeline d'enrichissement VALIDÉ." if ok
          else "⚠️  Pipeline exécuté mais structure incomplète.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
