"""
tests/test_llm_garde_fou.py — Garde-fou anti-hallucination du classement IA
==========================================================================
Un verdict qui désigne une discussion (« Discussion commune », « Identique »,
« Similaire ») doit citer un identifiant présent parmi les candidats fournis.
Le client OpenAI est simulé : aucun appel réseau.
"""

import json
import os
import sys
import types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from api.llm_semantic_engine import evaluate_similitude

AMENDEMENT = {"uid": "AMDT-1", "dispositif": "À l'alinéa 3, supprimer les mots : « chaque année ».",
              "article_vise": "Article 5"}
CANDIDATS = [{"id_discussion": "AMDT-2", "amendement": {"divisionArticleDesignation": "Article 5",
                                                       "dispositif": "Supprimer l'alinéa 3."}}]


def _faux_llm(monkeypatch, verdict):
    contenu = json.dumps(verdict, ensure_ascii=False)

    class FauxClient:
        def __init__(self, **_):
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=self._create))

        def _create(self, **_):
            message = types.SimpleNamespace(content=contenu)
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FauxClient))
    monkeypatch.delenv("VERCEL", raising=False)


def _verdict(statut, cible):
    return {"analyse_intention": "Les deux amendements visent l'alinéa 3.",
            "analyse_politique": "Sans objet.", "statut": statut,
            "id_discussion_cible": cible, "niveau_confiance": 0.9}


@pytest.mark.parametrize("statut", ["Discussion commune", "Identique", "Similaire"])
def test_identifiant_invente_rejete(monkeypatch, statut):
    _faux_llm(monkeypatch, _verdict(statut, "AMDT-INVENTE"))

    resultat = evaluate_similitude(AMENDEMENT, CANDIDATS, "http://localhost:1234/v1")

    assert resultat.statut == "NOUVEAU"
    assert resultat.niveau_confiance == 0.0
    assert "halluciné" in resultat.analyse_intention


def test_identifiant_present_accepte(monkeypatch):
    _faux_llm(monkeypatch, _verdict("Discussion commune", "AMDT-2"))

    resultat = evaluate_similitude(AMENDEMENT, CANDIDATS, "http://localhost:1234/v1")

    assert resultat.statut == "Discussion commune"
    assert resultat.id_discussion_cible == "AMDT-2"
