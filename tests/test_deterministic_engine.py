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


def test_deputes_resolver_signataire_and_groupe():
    """Validation de la résolution d'un signataire PA... et de son groupe via deputes_resolver."""
    from api.deputes_resolver import resolve_signataires

    # 1. Résolution par identifiant PA (Tricoteuses XVIIe : Corentin Le Fur)
    res = resolve_signataires("PA840979")
    assert "Corentin Le Fur" in res["auteurs_formatte"]
    assert res["groupe_principal"] == "DR"
    assert res["est_rapporteur"] is False

    # 2. Résolution avec dict Tricoteuses et qualité rapporteur
    res_rap = resolve_signataires({
        "auteur": {"acteurRef": "PA840979", "qualite": "Rapporteur"},
        "cosignataires": [{"acteurRef": "PA841701"}]
    })
    assert "Corentin Le Fur (DR)" in res_rap["auteurs_formatte"]
    assert "Léa Balage El Mariky (EcoS)" in res_rap["auteurs_formatte"]
    assert res_rap["est_rapporteur"] is True
    assert res_rap["groupe_principal"] == "DR"

    # 3. Fallback gracieux sur ID inconnu
    res_inconnu = resolve_signataires("PA99999999")
    assert res_inconnu["auteurs_formatte"] == "PA99999999"
    assert res_inconnu["groupe_principal"] == ""
    assert res_inconnu["est_rapporteur"] is False


def test_rapporteur_priority_sorting():
    """Vérifie la priorité de classement accordée à un amendement de rapporteur à portée égale."""
    a_depute = EnrichedAmendment(
        amendement_uid="AMDT-DEP-1",
        numero_long="1",
        dispositif_raw="<p>Supprimer l'article 1er.</p>",
        article_vise="ART. 1",
        auteur_ref="PA000001",
        est_rapporteur=False,
    )
    a_rapporteur = EnrichedAmendment(
        amendement_uid="AMDT-RAP-10",
        numero_long="10",
        dispositif_raw="<p>Supprimer l'article 1er.</p>",
        article_vise="ART. 1",
        auteur_ref="PA111111",
        est_rapporteur=True,
    )

    # On injecte le député en premier dans la liste
    sorted_amends = process_deterministic_sorting([a_depute, a_rapporteur])

    # L'amendement du rapporteur doit obligatoirement être classé en tête (index 0)
    assert sorted_amends[0].amendement_uid == "AMDT-RAP-10"
    assert sorted_amends[0].est_rapporteur is True
    assert sorted_amends[1].amendement_uid == "AMDT-DEP-1"


def test_texte_loi_initial_prompt_injection():
    """Confirme l'insertion du bloc <TEXTE_LOI_INITIAL> dans le prompt LLM lorsque la référence est fournie."""
    from api.llm_semantic_engine import generate_classification_prompt

    amendement = {
        "amendement": {
            "uid": "AMDT-TEST-LOI",
            "numeroLong": "42",
            "dispositif": "À la première phrase, substituer au mot « rouge » le mot « vert ».",
            "exposeSommaire": "Clarification.",
            "divisionArticleDesignation": "Article 1er",
        },
        "auteur": {"nom": "Monnier", "prenom": "Laurent"},
        "dossier": {"titre": "Projet de loi de finances"},
    }

    texte_loi = "Le présent article prévoit que les feux de signalisation sont de couleur rouge."

    # 1. Sans texte de référence
    prompt_sans = generate_classification_prompt(amendement)
    assert "<TEXTE_LOI_INITIAL" not in prompt_sans

    # 2. Avec texte de référence
    prompt_avec = generate_classification_prompt(amendement, texte_loi_reference=texte_loi)
    assert '<TEXTE_LOI_INITIAL article="Article 1er">' in prompt_avec
    assert texte_loi in prompt_avec
    assert "</TEXTE_LOI_INITIAL>" in prompt_avec
    assert "Consigne stricte : Tu dois analyser l'impact des amendements" in prompt_avec


def test_textes_resolver_nominal():
    """Vérifie que le chargement de PIONANR5L17B0149 résout bien les articles ARTICLE PREMIER et ARTICLE 2."""
    from api.textes_resolver import get_textes_reference

    articles = get_textes_reference("PIONANR5L17B0149")
    assert len(articles) == 2
    assert "ARTICLE PREMIER" in articles
    assert "ARTICLE 2" in articles
    assert "72-4 de la Constitution" in articles["ARTICLE PREMIER"]
    assert "88-3 de la Constitution est abrogé" in articles["ARTICLE 2"]


def test_textes_resolver_normalization_match():
    """Vérifie que ART. PREMIER, Article 1er et ARTICLE PREMIER matchent tous le même texte d'article."""
    from api.textes_resolver import get_textes_reference, match_article_reference

    articles = get_textes_reference("PIONANR5L17B0149")
    txt_premier = articles["ARTICLE PREMIER"]

    m1 = match_article_reference(articles, "ARTICLE PREMIER")
    m2 = match_article_reference(articles, "Article 1er")
    m3 = match_article_reference(articles, "ART. PREMIER")
    m4 = match_article_reference(articles, "1")

    assert m1 == txt_premier
    assert m2 == txt_premier
    assert m3 == txt_premier
    assert m4 == txt_premier

    m_art2 = match_article_reference(articles, "ART. 2")
    assert m_art2 == articles["ARTICLE 2"]


def test_textes_resolver_fallback():
    """Vérifie qu'un identifiant inexistant retourne {} sans crash."""
    from api.textes_resolver import get_textes_reference, match_article_reference

    inconnu = get_textes_reference("DOSSIER_INCONNU_99999")
    assert inconnu == {}

    none_match = match_article_reference(inconnu, "ART. 1")
    assert none_match is None


def test_auto_injection_texte_in_enriched_amendment():
    """Vérifie qu'un amendement visant l'Article PREMIER reçoit automatiquement son texte_loi_reference."""
    from api.index import _inject_textes_reference
    from api.textes_resolver import get_textes_reference

    articles = get_textes_reference("PIONANR5L17B0149")
    a = EnrichedAmendment(
        amendement_uid="AMDT-AUTO-REF",
        numero_long="42",
        dispositif_raw="<p>Modifier l'article premier</p>",
        article_vise="ART. PREMIER",
        auteur_ref="PA841749",
    )

    assert a.texte_loi_reference is None
    _inject_textes_reference([a], articles)
    assert a.texte_loi_reference is not None
    assert "72-4 de la Constitution" in a.texte_loi_reference


def test_deputes_tricoteuses_real_data():
    """Valide la résolution en clair et le groupe politique de PA840979, PA719890 et PA330909."""
    from api.deputes_resolver import resolve_signataires

    # 1. PA840979 : Corentin Le Fur (DR)
    res1 = resolve_signataires("PA840979")
    assert "Corentin Le Fur" in res1["auteurs_formatte"]
    assert res1["groupe_principal"] == "DR"
    assert "DR" in res1["auteurs_formatte"]

    # 2. PA719890 : Danielle Brulebois (EPR)
    res2 = resolve_signataires("PA719890")
    assert "Danielle Brulebois" in res2["auteurs_formatte"]
    assert res2["groupe_principal"] == "EPR"
    assert "EPR" in res2["auteurs_formatte"]

    # 3. PA330909 : Vincent Descoeur (DR)
    res3 = resolve_signataires("PA330909")
    assert "Vincent Descoeur" in res3["auteurs_formatte"]
    assert res3["groupe_principal"] == "DR"
    assert "DR" in res3["auteurs_formatte"]


def test_boilerplate_accents_retire_avant_publication():
    """
    Deux amendements avec le dispositif <p>Retiré avant publication.</p>
    doivent ressortir tous deux Isolé et JAMAIS Identique.
    """
    from api.deterministic_engine import process_deterministic_sorting
    from api.schemas import EnrichedAmendment, StatutMecanique

    a1 = EnrichedAmendment(
        amendement_uid="AMDT-CL31",
        numero_long="CL31",
        dispositif_raw="<p>Retiré avant publication.</p>",
        article_vise="Article 1er",
        auteur_ref="PA840979",
    )
    a2 = EnrichedAmendment(
        amendement_uid="AMDT-CL32",
        numero_long="CL32",
        dispositif_raw="<p>Retiré avant publication.</p>",
        article_vise="Article 1er",
        auteur_ref="PA719890",
    )

    result = process_deterministic_sorting([a1, a2])
    res_map = {a.amendement_uid: a for a in result}

    cl31 = res_map["AMDT-CL31"]
    cl32 = res_map["AMDT-CL32"]

    assert cl31.statut_mecanique == StatutMecanique.ISOLE_MECANIQUE
    assert cl32.statut_mecanique == StatutMecanique.ISOLE_MECANIQUE
    assert cl31.statut_mecanique != StatutMecanique.IDENTIQUE_MECANIQUE
    assert cl32.statut_mecanique != StatutMecanique.IDENTIQUE_MECANIQUE
    assert cl31.skip_llm is True
    assert cl32.skip_llm is True
    assert cl31.alerte_couleur == "gris"
    assert cl32.alerte_couleur == "gris"


def test_nested_contenu_auteur_dispositif_extraction():
    """Vérifie que le dispositif extrait depuis corps.contenuAuteur.dispositif n'est pas 'Non renseigné'."""
    from api.index import extract_dispositif_raw, normaliser_amendement, _build_enriched

    raw_an = {
        "amendement": {
            "uid": "AMANR5L17PO845413B0149P0D1N000001",
            "identification": {"numeroLong": "CL1"},
            "corps": {
                "cartoucheInformatif": {
                    "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                    "@xsi:nil": "true",
                },
                "contenuAuteur": {
                    "dispositif": "<p>Supprimer cet article.</p>",
                    "exposeSommaire": "<p>Exposé sommaire explicatif.</p>",
                },
            },
            "pointeurFragmentTexte": {
                "division": {
                    "titre": "Article PREMIER",
                    "articleDesignation": "Article premier",
                }
            },
            "signataires": {
                "auteur": {
                    "acteurRef": "PA842187",
                    "groupePolitiqueRef": "PO845413",
                }
            },
        }
    }

    # 1. extract_dispositif_raw direct
    disp = extract_dispositif_raw(raw_an["amendement"])
    assert disp == "<p>Supprimer cet article.</p>"
    assert disp != "Non renseigné"

    # 2. normaliser_amendement
    norm = normaliser_amendement(raw_an, 0)
    assert norm["dispositif"] == "<p>Supprimer cet article.</p>"
    assert norm["texte"] == "<p>Supprimer cet article.</p>"
    assert norm["dispositif"] != "Non renseigné"
    assert norm["article"] == "Article PREMIER"  # Pas de doublon 'Article Article PREMIER'

    # 3. _build_enriched
    enriched = _build_enriched(raw_an, 0)
    assert enriched.dispositif_raw == "<p>Supprimer cet article.</p>"
    assert enriched.dispositif_raw != "Non renseigné"


def test_groupe_politique_ref_mapping_lfi_nfp():
    """Vérifie qu'un amendement avec groupePolitiqueRef = 'PO845413' ressort avec groupe = 'LFI-NFP'."""
    from api.deputes_resolver import resolve_signataires, MAPPING_ORGANES_XVII
    from api.index import _build_enriched, _to_frontend
    from api.deterministic_engine import process_deterministic_sorting

    raw_an = {
        "amendement": {
            "uid": "AMANR5L17-CL1",
            "identification": {"numeroLong": "CL1"},
            "corps": {
                "contenuAuteur": {
                    "dispositif": "<p>Supprimer cet article.</p>",
                }
            },
            "pointeurFragmentTexte": {
                "division": {"titre": "Article 1er"}
            },
            "signataires": {
                "auteur": {
                    "acteurRef": "PA842187",
                    "groupePolitiqueRef": "PO845413",
                }
            },
        }
    }

    # 1. deputes_resolver direct
    sig_res = resolve_signataires(raw_an["amendement"]["signataires"])
    assert sig_res["groupe_principal"] == "LFI-NFP"
    assert MAPPING_ORGANES_XVII.get("PO845413") == "LFI-NFP"

    # 2. _build_enriched
    enriched = _build_enriched(raw_an, 0)
    assert enriched.groupe_politique_ref == "PO845413"
    assert enriched.groupe_politique == "LFI-NFP"

    # 3. process_deterministic_sorting
    sorted_amends = process_deterministic_sorting([enriched])
    assert sorted_amends[0].groupe_politique == "LFI-NFP"

    # 4. _to_frontend
    front_dict = _to_frontend(sorted_amends[0])
    assert front_dict["groupe"] == "LFI-NFP"
    assert front_dict["groupe_politique"] == "LFI-NFP"
    assert front_dict["groupRef"] == "PO845413"


def test_identical_supprimer_cet_article():
    """Vérifie que deux amendements avec le dispositif '<p>Supprimer cet article.</p>' ressortent en Identique."""
    from api.deterministic_engine import process_deterministic_sorting
    from api.schemas import EnrichedAmendment, StatutMecanique

    a1 = EnrichedAmendment(
        amendement_uid="AMDT-SUPP-1",
        numero_long="CL1",
        dispositif_raw="<p>Supprimer cet article.</p>",
        article_vise="Article 1er",
        auteur_ref="PA842187",
    )
    a2 = EnrichedAmendment(
        amendement_uid="AMDT-SUPP-2",
        numero_long="CL2",
        dispositif_raw="<p>Supprimer cet article.</p>",
        article_vise="Article 1er",
        auteur_ref="PA840915",
    )

    res = process_deterministic_sorting([a1, a2])
    assert res[0].amendement_uid == "AMDT-SUPP-1"
    assert res[1].amendement_uid == "AMDT-SUPP-2"
    assert res[1].statut_mecanique == StatutMecanique.IDENTIQUE_MECANIQUE
    assert res[1].skip_llm is True
    assert res[1].groupe_identique_id is not None
    assert "Identique mécanique" in res[1].justification_mecanique


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
        test_deputes_resolver_signataire_and_groupe,
        test_rapporteur_priority_sorting,
        test_texte_loi_initial_prompt_injection,
        test_textes_resolver_nominal,
        test_textes_resolver_normalization_match,
        test_textes_resolver_fallback,
        test_auto_injection_texte_in_enriched_amendment,
        test_deputes_tricoteuses_real_data,
        test_boilerplate_accents_retire_avant_publication,
        test_nested_contenu_auteur_dispositif_extraction,
        test_groupe_politique_ref_mapping_lfi_nfp,
        test_identical_supprimer_cet_article,
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
