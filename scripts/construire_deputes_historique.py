"""
scripts/construire_deputes_historique.py — Référentiel des députés depuis 1997
==============================================================================
Construit api/data/deputes_historique.json à partir du jeu officiel
« Historique des députés » (AMO30, data.assemblee-nationale.fr) :
tous les députés et anciens députés élus depuis la XIe législature (1997).

Le résolveur (api/deputes_resolver.py) s'en sert en repli de
deputes_active.json : un amendement cosigné par un député ayant quitté
l'Assemblée (remplacé, démissionnaire, ancienne législature) affiche ainsi
un nom et un groupe au lieu d'un matricule PA….

Usage (après téléchargement et extraction de l'archive JSON) :
    curl -o amo30.zip https://data.assemblee-nationale.fr/static/openData/repository/17/amo/tous_acteurs_mandats_organes_xi_legislature/AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip
    unzip amo30.zip -d amo30
    python scripts/construire_deputes_historique.py amo30/json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from api.deputes_resolver import MAPPING_ORGANES_XVII  # noqa: E402

SORTIE = RACINE / "api" / "data" / "deputes_historique.json"


def _en_liste(valeur):
    if valeur is None:
        return []
    return valeur if isinstance(valeur, list) else [valeur]


def _sigle_groupe(dossier_organes: Path, organe_ref: str, cache: dict[str, str]) -> str:
    """Sigle du groupe : celui de Bourbon.IA pour la XVIIe, sinon le libellé abrégé officiel."""
    if organe_ref in MAPPING_ORGANES_XVII:
        return MAPPING_ORGANES_XVII[organe_ref]
    if organe_ref not in cache:
        fichier = dossier_organes / f"{organe_ref}.json"
        organe = json.loads(fichier.read_text(encoding="utf-8"))["organe"] if fichier.is_file() else {}
        cache[organe_ref] = organe.get("libelleAbrev") or organe.get("libelleAbrege") or ""
    return cache[organe_ref]


def construire(dossier_json: Path) -> dict[str, dict]:
    dossier_organes = dossier_json / "organe"
    cache_organes: dict[str, str] = {}
    deputes: dict[str, dict] = {}

    for fichier in sorted((dossier_json / "acteur").glob("PA*.json")):
        acteur = json.loads(fichier.read_text(encoding="utf-8"))["acteur"]
        ident = acteur["etatCivil"]["ident"]
        mandats = _en_liste((acteur.get("mandats") or {}).get("mandat"))

        legislatures = sorted(
            {int(m["legislature"]) for m in mandats if m.get("typeOrgane") == "ASSEMBLEE" and m.get("legislature")}
        )
        if not legislatures:
            continue  # pas de mandat de député dans le jeu

        # Dernier groupe politique : mandat GP le plus récent.
        groupes = [m for m in mandats if m.get("typeOrgane") == "GP"]
        dernier = max(groupes, key=lambda m: m.get("dateDebut") or "", default=None)
        organe_ref = (dernier or {}).get("organes", {}).get("organeRef", "") if dernier else ""

        deputes[acteur["uid"]["#text"] if isinstance(acteur["uid"], dict) else acteur["uid"]] = {
            "nom": f"{ident['prenom']} {ident['nom']}".strip(),
            "groupe": _sigle_groupe(dossier_organes, organe_ref, cache_organes) if organe_ref else "",
            "organeRef": organe_ref,
            "legislatures": legislatures,
        }

    return deputes


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    resultat = construire(Path(sys.argv[1]))
    SORTIE.write_text(json.dumps(resultat, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(f"{len(resultat)} députés écrits dans {SORTIE.relative_to(RACINE)}")
