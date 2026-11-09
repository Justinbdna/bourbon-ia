"""
tests/test_seance_pleniere.py — Règle « séance plénière → discussion commune »
==============================================================================
Les amendements examinés en séance plénière (organe PO838901), encore isolés ou
en attente d'IA, sont classés en discussion commune sans IA ; identiques,
doublons et irrecevables gardent leur statut ; les amendements de commission
ne sont pas concernés.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.deterministic_engine import process_deterministic_sorting
from api.index import _to_frontend
from api.schemas import EnrichedAmendment, StatutMecanique

SEANCE = "PO838901"
COMMISSION = "PO419604"


def _amdt(uid, dispositif, organe, auteur="PA1", article="ART. 5"):
    return EnrichedAmendment(
        amendement_uid=uid,
        numero_long=uid,
        dispositif_raw=f"<p>{dispositif}</p>",
        article_vise=article,
        auteur_ref=auteur,
        commission_ref=organe,
    )


def test_seance_isolee_et_ambigue_passent_en_discussion_commune():
    isole = _amdt("S1", "Supprimer cet article.", SEANCE, article="ART. 9")
    ambigu_1 = _amdt("S2", "À l'alinéa 3, supprimer le mot « annuel ».", SEANCE, auteur="PA2")
    ambigu_2 = _amdt("S3", "À l'alinéa 3, remplacer le mot « annuel » par « biennal ».", SEANCE, auteur="PA3")

    resultat = {a.amendement_uid: a for a in process_deterministic_sorting([isole, ambigu_1, ambigu_2])}

    for uid in ("S1", "S2", "S3"):
        assert resultat[uid].statut_mecanique == StatutMecanique.SEANCE_PLENIERE
        assert resultat[uid].skip_llm is True
    front = _to_frontend(resultat["S1"])
    assert front["resultat_ia"]["statut"] == "Discussion commune"
    assert front["_skipLLM"] is True


def test_identiques_doublons_et_irrecevables_gardent_leur_statut():
    original = _amdt("S4", "À l'alinéa 2, supprimer le mot « public ».", SEANCE, auteur="PA4")
    identique = _amdt("S5", "À l'alinéa 2, supprimer le mot « public ».", SEANCE, auteur="PA5")
    doublon = _amdt("S6", "À l'alinéa 2, supprimer le mot « public ».", SEANCE, auteur="PA4")
    irrecevable = _amdt("S7", "", SEANCE, auteur="PA6")

    resultat = {a.amendement_uid: a for a in process_deterministic_sorting([original, identique, doublon, irrecevable])}

    assert resultat["S5"].statut_mecanique == StatutMecanique.IDENTIQUE_MECANIQUE
    assert resultat["S6"].statut_mecanique == StatutMecanique.DOUBLON_MECANIQUE
    assert resultat["S7"].statut_mecanique == StatutMecanique.ISOLE_MECANIQUE


def test_amendements_de_commission_non_concernes():
    seul = _amdt("C1", "Supprimer cet article.", COMMISSION, article="ART. 9")

    resultat = process_deterministic_sorting([seul])

    assert resultat[0].statut_mecanique == StatutMecanique.ISOLE_MECANIQUE
