"""
tests/test_textes_resolver.py — Récupération du texte de loi de référence
=========================================================================
Vérifie la conversion d'un document Tricoteuses en articles et le repli
« fichier local → API Tricoteuses », sans appel réseau (API simulée).
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import api.textes_resolver as tr
import api.tricoteuses_client as tc

DOCUMENT = {
    "uid": "PRJLTEST",
    "titrePrincipalCourt": "Texte de test",
    "subdivisions": [
        {"hash": "h-titre", "type": "Titre", "titre": "TITRE IER", "sequence": 0},
        {"hash": "h3", "type": "Article", "titre": "Article 3", "sequence": 2},
        {"hash": "h3b", "type": "Article", "titre": "Article 3 bis (nouveau)", "sequence": 3},
        {"hash": "h1", "type": "Article", "titre": "Article 1er", "sequence": 1},
        {"hash": "hvide", "type": "Article", "titre": "Article 4", "sequence": 4},
    ],
    "alineas": [
        {"numero": 1, "texte": "Deuxième alinéa de l'article 3.", "articleRefHash": "h3"},
        {"numero": 0, "texte": "Premier alinéa de l'article 3.", "articleRefHash": "h3"},
        {"numero": 0, "texte": "Texte de l'article 3 bis.", "articleRefHash": "h3b"},
        {"numero": 0, "texte": "Texte de l'article premier.", "articleRefHash": "h1"},
    ],
}


def _reinitialiser(monkeypatch, tmp_path):
    monkeypatch.setattr(tr, "TEXTES_DIR", tmp_path)
    monkeypatch.setattr(tr, "_TEXTES_CACHE", {})
    monkeypatch.setattr(tr, "_ECHECS_DISTANTS", {})
    monkeypatch.delenv("BOURBON_TEXTES_DISTANTS", raising=False)


def test_articles_depuis_document_ordre_numerotation_et_titres():
    articles = tr.articles_depuis_document(DOCUMENT)

    assert list(articles) == ["Article 1er", "Article 3", "Article 3 bis"]
    assert articles["Article 3"] == "(1) Premier alinéa de l'article 3.\n(2) Deuxième alinéa de l'article 3."
    assert "Article 4" not in articles  # article sans alinéa ignoré


def test_article_bis_ne_recoit_pas_le_texte_de_l_article_de_base():
    articles = tr.articles_depuis_document(DOCUMENT)

    assert tr.match_article_reference(articles, "Article 3 bis") == "(1) Texte de l'article 3 bis."
    assert tr.match_article_reference(articles, "Article PREMIER") == "(1) Texte de l'article premier."


def test_repli_tricoteuses_quand_pas_de_fichier_local(monkeypatch, tmp_path):
    _reinitialiser(monkeypatch, tmp_path)
    appels = []

    def faux_request(path, params=None, timeout=None):
        appels.append(path)
        return {"data": DOCUMENT, "pagination": {}}

    monkeypatch.setattr(tc, "_request", faux_request)

    assert "Article 3 bis" in tr.get_textes_reference("PRJLTEST")
    assert tr.get_textes_reference("PRJLTEST")  # second appel servi par le cache
    assert appels == ["/v2/documents/PRJLTEST"]


def test_echec_reseau_renvoie_vide_et_n_est_pas_reessaye_immediatement(monkeypatch, tmp_path):
    _reinitialiser(monkeypatch, tmp_path)
    appels = []

    def faux_request(path, params=None, timeout=None):
        appels.append(path)
        raise tc.TricoteusesError("panne simulée")

    monkeypatch.setattr(tc, "_request", faux_request)

    assert tr.get_textes_reference("PRJLTEST") == {}
    assert tr.get_textes_reference("PRJLTEST") == {}
    assert len(appels) == 1


def test_mode_hors_ligne_desactive_l_appel_distant(monkeypatch, tmp_path):
    _reinitialiser(monkeypatch, tmp_path)
    monkeypatch.setenv("BOURBON_TEXTES_DISTANTS", "0")

    def faux_request(path, params=None, timeout=None):
        raise AssertionError("aucun appel réseau attendu en mode hors-ligne")

    monkeypatch.setattr(tc, "_request", faux_request)

    assert tr.get_textes_reference("PRJLTEST") == {}


def test_fichier_local_prioritaire(monkeypatch, tmp_path):
    _reinitialiser(monkeypatch, tmp_path)
    (tmp_path / "PRJLTEST.json").write_text('{"articles": {"Article 1er": "Version locale."}}', encoding="utf-8")

    def faux_request(path, params=None, timeout=None):
        raise AssertionError("le fichier local doit suffire")

    monkeypatch.setattr(tc, "_request", faux_request)

    assert tr.get_textes_reference("PRJLTEST") == {"Article 1er": "Version locale."}
