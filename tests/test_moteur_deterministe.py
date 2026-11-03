"""
Tests unitaires et d'intégration du moteur déterministe légistique (POST /api/v2/classer-regles).
Valide la performance (< 300 ms sur 341 amendements), la concordance à 100 % avec le Golden Dataset
JOP 2030, l'arbre de décision parlementaire (Règles A, B, C, D, E), l'empreinte textuelle ([Id.])
et la préservation des alertes Article 40 / non-normatives.
"""

import json
import time
from pathlib import Path
from fastapi.testclient import TestClient

from api.index import app
from api.services.deterministic_classifier import (
    classer_par_regles,
    nettoyer_dispositif,
    normaliser_fond_textuel,
    similarite_levenshtein,
    extraire_plage_alineas,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
SAMPLE_PATH = ROOT_DIR / "public" / "sample-amendments.json"
GOLDEN_PATH = ROOT_DIR / "reports" / "temoin_classification_golden.json"

client = TestClient(app)


def test_normalisation_et_similarite_levenshtein():
    """Vérifie la normalisation de l'empreinte textuelle et le seuil Levenshtein > 0.98."""
    t1 = "<p>À l’alinéa 3, substituer au montant : « 10\xa0000 € » le montant : « 25 000 € ».</p>"
    t2 = "A l'alinéa 3, substituer au montant : \"10 000 €\" le montant : \"25 000 €\""
    fp1 = normaliser_fond_textuel(nettoyer_dispositif(t1))
    fp2 = normaliser_fond_textuel(nettoyer_dispositif(t2))
    assert fp1 == fp2
    assert similarite_levenshtein(fp1, fp2) == 1.0


def test_extraction_plage_alineas():
    """Vérifie la détection des plages d'alinéas (Règle D : ex. alinéas 8 à 13 vs alinéas 9 et 10)."""
    s1 = extraire_plage_alineas("Supprimer les alinéas 8 à 13.", None)
    s2 = extraire_plage_alineas("Aux alinéas 9 et 10, substituer aux mots...", None)
    assert s1 == {8, 9, 10, 11, 12, 13}
    assert s2 == {9, 10}
    assert bool(s1 & s2) is True


def test_arbre_decision_synthetique_regles_a_b_c_d_e():
    """
    Teste l'arbre de décision parlementaire pur sur un lot synthétique hors JOP 2030 :
    - Identiques ([Id.]) sur l'Article 2 (suppression totale en doublon)
    - Règle B : Réécriture globale de l'Article 4 vs modification de l'alinéa 2 de l'Article 4
    - Règle D : Plage d'alinéas 8 à 13 vs alinéa 10 sur l'Article 5
    - Règle E : Amendements isolés sur des alinéas distincts (alinéa 1 vs alinéa 7 sur l'Article 6)
    """
    lot_synthetique = [
        # Identiques sur Article 2
        {
            "id": "SYN-1",
            "numero": "1001",
            "article": "Article 2",
            "dispositif": "Supprimer cet article.",
        },
        {
            "id": "SYN-2",
            "numero": "1002",
            "article": "Article 2",
            "dispositif": "<p>Supprimer cet article.</p>",
        },
        # Règle B : Réécriture globale vs alinéa spécifique sur Article 4
        {
            "id": "SYN-3",
            "numero": "1003",
            "article": "Article 4",
            "dispositif": "Rédiger ainsi cet article : « Art. 4. – Le présent article entre en vigueur en 2027. »",
        },
        {
            "id": "SYN-4",
            "numero": "1004",
            "article": "Article 4",
            "dispositif": "À l'alinéa 2, substituer à l'année : « 2026 » l'année : « 2028 ».",
        },
        # Règle D : Chevauchement de plage d'alinéas sur Article 5
        {
            "id": "SYN-5",
            "numero": "1005",
            "article": "Article 5",
            "dispositif": "Supprimer les alinéas 8 à 13.",
        },
        {
            "id": "SYN-6",
            "numero": "1006",
            "article": "Article 5",
            "dispositif": "À l'alinéa 10, supprimer les mots : « à titre expérimental ».",
        },
        # Règle E : Isolés sur alinéas distincts d'Article 6
        {
            "id": "SYN-7",
            "numero": "1007",
            "article": "Article 6",
            "dispositif": "À l'alinéa 1, substituer au mot : « peut » le mot : « doit ».",
        },
        {
            "id": "SYN-8",
            "numero": "1008",
            "article": "Article 6",
            "dispositif": "Compléter l'alinéa 7 par les mots : « après avis de la commission ».",
        },
    ]

    res = classer_par_regles(lot_synthetique)
    by_num = {a["numero"]: a for a in res["amendements"]}

    # Identiques sur Article 2
    assert by_num["1001"]["statut"] == "Identique"
    assert by_num["1002"]["statut"] == "Identique"
    assert by_num["1001"]["groupe_conflit_id"] == by_num["1002"]["groupe_conflit_id"]
    assert by_num["1001"]["groupe_conflit_id"].startswith("id_")

    # Règle B sur Article 4
    assert by_num["1003"]["statut"] == "Discussion commune"
    assert by_num["1004"]["statut"] == "Discussion commune"
    assert by_num["1003"]["groupe_conflit_id"] == by_num["1004"]["groupe_conflit_id"]
    assert by_num["1003"]["cible_numero"] == "1004"

    # Règle D sur Article 5
    assert by_num["1005"]["statut"] == "Discussion commune"
    assert by_num["1006"]["statut"] == "Discussion commune"
    assert by_num["1005"]["groupe_conflit_id"] == by_num["1006"]["groupe_conflit_id"]

    # Règle E sur Article 6
    assert by_num["1007"]["statut"] == "Isolé"
    assert by_num["1008"]["statut"] == "Isolé"
    assert by_num["1007"]["groupe_conflit_id"] is None
    assert by_num["1008"]["groupe_conflit_id"] is None


def test_route_classer_regles_jop2030_341_amendements():
    """
    Valide POST /api/v2/classer-regles sur les 341 amendements JOP 2030 :
    - Temps d'exécution < 300 ms
    - 122 Discussions communes, 120 Identiques (54 pivots + 66 suiveurs), 99 Isolés
    - Concordance de 100 % avec le Golden Dataset
    - Présence des identiques et discussions communes sur Article PREMIER, Article 3 BIS et Article 12
    """
    raw_amendements = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    golden_data = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    t0 = time.perf_counter()
    response = client.post("/api/v2/classer-regles", json={"amendements": raw_amendements})
    elapsed_http_ms = (time.perf_counter() - t0) * 1000.0

    assert response.status_code == 200
    payload = response.json()

    assert payload["statut"] == "success"
    assert payload["total"] == 341
    assert payload["duree_ms"] < 300, f"Moteur trop lent : {payload['duree_ms']} ms (attendu < 300 ms)"
    assert elapsed_http_ms < 500

    stats = payload["statistiques"]
    assert stats["discussions_communes"] == 122
    assert stats["identiques"] == 120
    assert stats["isoles"] == 99

    classified = payload["amendements"]
    assert len(classified) == 341

    # Vérification de concordance sur les Discussions communes et Identiques avec le Golden Dataset
    by_num = {str(a["numero"]): a for a in classified}
    for num, gold in golden_data.items():
        am = by_num[str(num)]
        if gold["statut_temoin"] == "Discussion commune":
            assert am["statut"] == "Discussion commune", f"Mismatch sur n° {num}"
            assert am["groupe_conflit_id"] is not None and am["groupe_conflit_id"].startswith("dc_")
            assert am["cible_numero"] == str(gold["cible_discussion"])
        elif gold["statut_temoin"] == "Identique":
            assert am["statut"] == "Identique", f"Mismatch identique sur n° {num}"
            assert am["groupe_conflit_id"] is not None and am["groupe_conflit_id"].startswith("id_")
            assert am["cible_numero"] == str(gold["cible_discussion"])

    # Vérification spécifique sur Article PREMIER, Article 3 BIS et Article 12
    art1_dc = [a for a in classified if a["article_vise"] == "PREMIER" and a["statut"] == "Discussion commune"]
    art3bis_dc = [a for a in classified if a["article_vise"] == "3 BIS" and a["statut"] == "Discussion commune"]
    art3bis_id = [a for a in classified if a["article_vise"] == "3 BIS" and a["statut"] == "Identique"]
    art12_dc = [a for a in classified if a["article_vise"] == "12" and a["statut"] == "Discussion commune"]
    art12_id = [a for a in classified if a["article_vise"] == "12" and a["statut"] == "Identique"]

    assert len(art1_dc) >= 2
    assert len(art3bis_dc) >= 4
    assert len(art3bis_id) >= 4
    assert len(art12_dc) >= 2
    assert len(art12_id) >= 2

    # Vérification de la préservation des alertes Article 40 (sans gage) et des gages détectés
    alertes_40 = [a for a in classified if a.get("alerte_recevabilite_art40") is True]
    gages_detectes = [a for a in classified if a.get("est_gage") is True]
    assert len(alertes_40) >= 3
    assert len(gages_detectes) >= 1
