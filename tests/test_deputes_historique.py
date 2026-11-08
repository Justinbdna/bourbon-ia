"""
tests/test_deputes_historique.py — Repli sur l'historique des députés (AMO30)
============================================================================
Un cosignataire ayant quitté l'Assemblée (absent de deputes_active.json) est
résolu par l'historique ; un député en exercice garde sa fiche courante ; la
recherche approchée par nom de famille n'utilise pas l'historique.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api import deputes_resolver
from api.deputes_resolver import get_depute_info, resolve_signataires, resolve_single_signataire

ACTIFS = {"PA1": {"nom": "Alice Martin", "groupe": "EPR", "organeRef": "PO845407"}}
HISTORIQUE = {
    "PA1": {"nom": "Alice Martin", "groupe": "LAREM", "organeRef": "PO730964", "legislatures": [15, 17]},
    "PA2": {"nom": "Bernard Ancien", "groupe": "DR", "organeRef": "PO845425", "legislatures": [16, 17]},
    "PA3": {"nom": "Claire Dupont-Lajoie", "groupe": "UMP", "organeRef": "PO656006", "legislatures": [13]},
}


def _referentiels(monkeypatch):
    monkeypatch.setattr(deputes_resolver, "_DEPUTES_DB", dict(ACTIFS))
    monkeypatch.setattr(deputes_resolver, "_DEPUTES_HISTORIQUE", dict(HISTORIQUE))


def test_ancien_depute_resolu_par_matricule(monkeypatch):
    _referentiels(monkeypatch)

    assert resolve_single_signataire({"acteurRef": "PA2"}) == ("Bernard Ancien", "DR", False)
    assert resolve_signataires("PA2")["auteurs_formatte"] == "Bernard Ancien (DR)"


def test_depute_en_exercice_prioritaire(monkeypatch):
    _referentiels(monkeypatch)

    assert get_depute_info("PA1")["groupe"] == "EPR"


def test_nom_complet_exact_trouve_dans_historique(monkeypatch):
    _referentiels(monkeypatch)

    assert resolve_single_signataire("Claire Dupont-Lajoie") == ("Claire Dupont-Lajoie", "UMP", False)


def test_pas_de_recherche_approchee_dans_historique(monkeypatch):
    _referentiels(monkeypatch)

    # « Ancien » est le nom de famille d'un ancien député : pas de rapprochement.
    assert resolve_single_signataire("M. Ancien") == ("M. Ancien", "", False)


def test_referentiel_reel_couvre_les_cosignataires_du_jeu_exemple():
    """Les 10 cosignataires du jeu d'exemple absents de deputes_active.json."""
    for matricule in ("PA720386", "PA794478", "PA840171"):
        assert get_depute_info(matricule), matricule
