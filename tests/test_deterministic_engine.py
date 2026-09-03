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

    assert result[0].statut_mecanique == StatutMecanique.NOUVEAU
    assert result[1].statut_mecanique == StatutMecanique.IDENTIQUE_MECANIQUE
    assert result[1].groupe_identique_id is not None


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

    assert result[0].statut_mecanique == StatutMecanique.NOUVEAU
    assert result[1].statut_mecanique == StatutMecanique.IDENTIQUE_MECANIQUE


def test_different_text_on_same_alinea_forms_cluster_and_stays_nouveau():
    """Deux amendements en concurrence sur le même alinéa forment un cluster et restent NOUVEAU pour le LLM."""
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
        dispositif_raw="<p>Compléter l'alinéa 3 par les mots : « et des territoires ».</p>",
        article_vise="ART. 5",
        auteur_ref="PA000002",
    )

    result = process_deterministic_sorting([a1, a2])

    assert result[0].statut_mecanique == StatutMecanique.NOUVEAU
    assert result[1].statut_mecanique == StatutMecanique.NOUVEAU
    assert result[0].skip_llm is False
    assert result[1].skip_llm is False
    assert result[0].cluster_id is not None
    assert result[0].cluster_id == result[1].cluster_id


def test_single_amendment_on_alinea_is_isolated():
    """Un amendement seul sur son alinéa / point d'impact ressort obligatoirement Isolé avec skip_llm = True."""
    a_seul = EnrichedAmendment(
        amendement_uid="AMDT-SEUL-1",
        numero_long="101",
        dispositif_raw="<p>À l'alinéa 12, substituer au montant : « 100 » le montant : « 200 ».</p>",
        article_vise="ART. 3",
        auteur_ref="PA999001",
    )

    result = process_deterministic_sorting([a_seul])

    assert result[0].statut_mecanique == StatutMecanique.ISOLE_MECANIQUE
    assert result[0].skip_llm is True
    assert "Seul amendement" in result[0].justification_mecanique


def test_clustering_partitioning_scale_up():
    """Vérifie le partitionnement : 2 amendements sur l'alinéa 1 (cluster) et 1 seul sur l'alinéa 4 (isolé)."""
    a_al1_a = EnrichedAmendment(
        amendement_uid="AMDT-A",
        numero_long="1",
        dispositif_raw="<p>Supprimer l'alinéa 1.</p>",
        article_vise="ART. 2",
    )
    a_al1_b = EnrichedAmendment(
        amendement_uid="AMDT-B",
        numero_long="2",
        dispositif_raw="<p>Rédiger ainsi l'alinéa 1 : nouvelle rédaction.</p>",
        article_vise="ART. 2",
    )
    a_al4_seul = EnrichedAmendment(
        amendement_uid="AMDT-C",
        numero_long="3",
        dispositif_raw="<p>Compléter l'alinéa 4 par les mots suivants.</p>",
        article_vise="ART. 2",
    )

    result = process_deterministic_sorting([a_al1_a, a_al1_b, a_al4_seul])

    by_uid = {a.amendement_uid: a for a in result}

    # Les 2 sur l'alinéa 1 doivent être en cluster et rester NOUVEAU pour le LLM
    assert by_uid["AMDT-A"].statut_mecanique == StatutMecanique.NOUVEAU
    assert by_uid["AMDT-B"].statut_mecanique == StatutMecanique.NOUVEAU
    assert by_uid["AMDT-A"].skip_llm is False
    assert by_uid["AMDT-B"].skip_llm is False
    assert by_uid["AMDT-A"].cluster_id == by_uid["AMDT-B"].cluster_id

    # L'amendement seul sur l'alinéa 4 doit être isolé mécaniquement
    assert by_uid["AMDT-C"].statut_mecanique == StatutMecanique.ISOLE_MECANIQUE
    assert by_uid["AMDT-C"].skip_llm is True


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


def test_boilerplate_amendments_not_identical():
    """3 amendements avec 'Non renseigné' sur le même article ressortent Isolés et NON Identiques."""
    a1 = EnrichedAmendment(
        amendement_uid="AMDT-VIDE-1",
        numero_long="10",
        dispositif_raw="<p>Non renseigné</p>",
        article_vise="ART. 4",
        auteur_ref="PA0001",
    )
    a2 = EnrichedAmendment(
        amendement_uid="AMDT-VIDE-2",
        numero_long="11",
        dispositif_raw="<p>Non renseigné</p>",
        article_vise="ART. 4",
        auteur_ref="PA0002",
    )
    a3 = EnrichedAmendment(
        amendement_uid="AMDT-VIDE-3",
        numero_long="12",
        dispositif_raw="<p>Non renseigné</p>",
        article_vise="ART. 4",
        auteur_ref="PA0003",
    )

    results = process_deterministic_sorting([a1, a2, a3])

    for r in results:
        assert r.statut_mecanique == StatutMecanique.ISOLE_MECANIQUE
        assert r.skip_llm is True
        assert r.groupe_identique_id is None
        assert "non renseigné" in r.justification_mecanique.lower() or "irrecevable" in r.justification_mecanique.lower()


def test_competing_distinct_texts_have_skip_llm_false():
    """2 amendements aux textes distincts sur l'alinéa 1 d'un même article ont bien skip_llm = False."""
    a1 = EnrichedAmendment(
        amendement_uid="AMDT-COMPLEX-1",
        numero_long="21",
        dispositif_raw="<p>Supprimer l'alinéa 1.</p>",
        article_vise="ART. 6",
        auteur_ref="PA1001",
    )
    a2 = EnrichedAmendment(
        amendement_uid="AMDT-COMPLEX-2",
        numero_long="22",
        dispositif_raw="<p>Rédiger ainsi l'alinéa 1 : L'autorité administrative compétente statue dans un délai de trois mois.</p>",
        article_vise="ART. 6",
        auteur_ref="PA1002",
    )

    results = process_deterministic_sorting([a1, a2])

    assert len(results) == 2
    for r in results:
        assert r.statut_mecanique == StatutMecanique.NOUVEAU
        assert r.skip_llm is False
        assert r.cluster_id is not None
        assert "Cas complexe" in r.justification_mecanique


def test_in_memory_cache_ttl_and_eviction():
    """Valide lecture/écriture, expiration TTL et éviction du cache en mémoire RAM."""
    import time
    from api.cache_manager import InMemoryCache

    cache = InMemoryCache(max_entries=2, default_ttl=1)

    # 1. Écriture et lecture
    cache.set("AMD-1", {"statut": "Isolé", "analyse": "Test 1"}, ttl=1)
    hit = cache.get("AMD-1")
    assert hit is not None
    assert hit["statut"] == "Isolé"
    assert hit["cached"] is True

    # 2. Expiration TTL
    time.sleep(1.05)
    expired = cache.get("AMD-1")
    assert expired is None

    # 3. Éviction si capacité dépassée
    cache.set("AMD-A", {"statut": "Similaire"}, ttl=10)
    cache.set("AMD-B", {"statut": "Discussion commune"}, ttl=10)
    assert cache.size() == 2

    cache.set("AMD-C", {"statut": "Isolé"}, ttl=10)
    assert cache.size() == 2
    assert cache.get("AMD-A") is None
    assert cache.get("AMD-B") is not None
    assert cache.get("AMD-C") is not None

    # 4. Vidage
    cleared = cache.clear()
    assert cleared == 2
    assert cache.size() == 0


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
        test_different_text_on_same_alinea_forms_cluster_and_stays_nouveau,
        test_single_amendment_on_alinea_is_isolated,
        test_clustering_partitioning_scale_up,
        test_official_identique_flag,
        test_sorting_order_respects_hierarchy,
        test_boilerplate_amendments_not_identical,
        test_competing_distinct_texts_have_skip_llm_false,
        test_in_memory_cache_ttl_and_eviction,
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
