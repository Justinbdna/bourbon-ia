"""
tests/test_deterministic_engine.py — Tests unitaires du moteur déterministe
===========================================================================
Vérifie que la détection mécanique des identiques et doublons est infaillible.
"""

import sys
import os

# Ajouter la racine du projet au PYTHONPATH pour les imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.schemas import EnrichedAmendment, StatutMecanique
from api.deterministic_engine import normalize_text, process_deterministic_sorting, classify_point_impact


# ──────────────────────────────────────────────────────────────────────────
# Tests de normalisation
# ──────────────────────────────────────────────────────────────────────────

def test_normalize_strips_html():
    raw = '<p style="text-align: justify;">Compléter l&#x2019;alinéa&nbsp;2.</p>'
    result = normalize_text(raw)
    assert "<" not in result
    assert ">" not in result
    assert "alin" in result


def test_normalize_collapses_whitespace():
    raw = "   Supprimer   cet    article   "
    result = normalize_text(raw)
    assert result == "supprimer cet article"


def test_normalize_removes_punctuation():
    raw = "L'article 1er, alinéa 2 : « supprimé »."
    result = normalize_text(raw)
    assert "," not in result
    assert ":" not in result
    assert "«" not in result


def test_normalize_empty_string():
    assert normalize_text("") == ""
    assert normalize_text(None) == ""


# ──────────────────────────────────────────────────────────────────────────
# Tests de classification hiérarchique
# ──────────────────────────────────────────────────────────────────────────

def test_classify_suppression_article():
    _, impact = classify_point_impact("supprimer cet article")
    assert impact.value == "SUPPRESSION_ARTICLE"


def test_classify_redaction_alinea():
    _, impact = classify_point_impact("rediger ainsi lalinea 3")
    assert impact.value == "REDACTION_ALINEA"


def test_classify_point_restreint():
    _, impact = classify_point_impact("completer la premiere phrase de lalinea 2 par les mots")
    assert impact.value == "POINT_RESTREINT"


# ──────────────────────────────────────────────────────────────────────────
# Tests du moteur de tri principal
# ──────────────────────────────────────────────────────────────────────────

def test_identical_amendments_detected():
    """Deux amendements avec le même texte + même article mais auteurs différents → IDENTIQUE_MECANIQUE."""
    a1 = EnrichedAmendment(
        amendement_uid="AMDT-001",
        numero_long="1",
        dispositif_raw="<p>Supprimer l'alinéa 3.</p>",
        article_vise="ART. 5",
        auteur_ref="PA000001",
    )
    a2 = EnrichedAmendment(
        amendement_uid="AMDT-002",
        numero_long="2",
        dispositif_raw="<p>Supprimer l'alinéa 3.</p>",
        article_vise="ART. 5",
        auteur_ref="PA000002",
    )

    result = process_deterministic_sorting([a1, a2])

    assert result[0].statut_mecanique == StatutMecanique.IDENTIQUE_MECANIQUE
    assert result[1].statut_mecanique == StatutMecanique.IDENTIQUE_MECANIQUE
    assert result[0].groupe_identique_id == result[1].groupe_identique_id
    assert result[0].groupe_identique_id is not None


def test_doublon_same_author_detected():
    """Deux amendements avec le même texte + même article + même auteur → DOUBLON_MECANIQUE."""
    a1 = EnrichedAmendment(
        amendement_uid="AMDT-003",
        numero_long="3",
        dispositif_raw="<p>Rédiger ainsi cet article : blabla</p>",
        article_vise="ART. 1",
        auteur_ref="PA999999",
    )
    a2 = EnrichedAmendment(
        amendement_uid="AMDT-004",
        numero_long="4",
        dispositif_raw="<p>Rédiger ainsi cet article : blabla</p>",
        article_vise="ART. 1",
        auteur_ref="PA999999",
    )

    result = process_deterministic_sorting([a1, a2])

    assert result[0].statut_mecanique == StatutMecanique.DOUBLON_MECANIQUE
    assert result[1].statut_mecanique == StatutMecanique.DOUBLON_MECANIQUE


def test_different_text_stays_nouveau():
    """Deux amendements avec des textes différents restent NOUVEAU."""
    a1 = EnrichedAmendment(
        amendement_uid="AMDT-005",
        numero_long="5",
        dispositif_raw="<p>Supprimer l'alinéa 3.</p>",
        article_vise="ART. 5",
        auteur_ref="PA000001",
    )
    a2 = EnrichedAmendment(
        amendement_uid="AMDT-006",
        numero_long="6",
        dispositif_raw="<p>Compléter l'alinéa 7 par les mots : « et des territoires ».</p>",
        article_vise="ART. 5",
        auteur_ref="PA000002",
    )

    result = process_deterministic_sorting([a1, a2])

    assert result[0].statut_mecanique == StatutMecanique.NOUVEAU
    assert result[1].statut_mecanique == StatutMecanique.NOUVEAU


def test_official_identique_flag():
    """Un amendement marqué par l'AN comme identique → IDENTIQUE_OFFICIEL."""
    a1 = EnrichedAmendment(
        amendement_uid="AMDT-007",
        numero_long="7",
        dispositif_raw="<p>Test officiel.</p>",
        article_vise="ART. 2",
        auteur_ref="PA111111",
        est_identique_officiel=True,
        id_discussion_identique="DI-2026-001",
    )

    result = process_deterministic_sorting([a1])

    assert result[0].statut_mecanique == StatutMecanique.IDENTIQUE_OFFICIEL
    assert "discussion identique" in result[0].justification_mecanique


def test_sorting_order_respects_hierarchy():
    """Le tri final respecte la hiérarchie : Suppression > Rédaction > Point restreint."""
    a_restreint = EnrichedAmendment(
        amendement_uid="AMDT-R",
        numero_long="1",
        dispositif_raw="compléter la première phrase par les mots blabla",
        article_vise="ART. 1",
    )
    a_suppression = EnrichedAmendment(
        amendement_uid="AMDT-S",
        numero_long="2",
        dispositif_raw="supprimer cet article",
        article_vise="ART. 1",
    )

    result = process_deterministic_sorting([a_restreint, a_suppression])

    # La suppression doit arriver en premier
    assert result[0].amendement_uid == "AMDT-S"
    assert result[1].amendement_uid == "AMDT-R"


# ──────────────────────────────────────────────────────────────────────────
# Exécution directe
# ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_normalize_strips_html,
        test_normalize_collapses_whitespace,
        test_normalize_removes_punctuation,
        test_normalize_empty_string,
        test_classify_suppression_article,
        test_classify_redaction_alinea,
        test_classify_point_restreint,
        test_identical_amendments_detected,
        test_doublon_same_author_detected,
        test_different_text_stays_nouveau,
        test_official_identique_flag,
        test_sorting_order_respects_hierarchy,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ {t.__name__} — {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ {t.__name__} — Exception: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Résultat : {passed} passés, {failed} échoués sur {len(tests)} tests.")
    if failed == 0:
        print("🟢 TOUS LES TESTS PASSENT.")
    else:
        print("🔴 DES TESTS ONT ÉCHOUÉ.")
        exit(1)
