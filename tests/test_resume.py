"""
tests/test_resume.py — Résumé IA d'un amendement (route /api/v2/resumer)
=======================================================================
Vérifie le résumé sans appel réseau : le client OpenAI est simulé.
"""

import os
import sys
import types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

import api.llm_semantic_engine as moteur
from api.index import app

client = TestClient(app)

PAYLOAD = {
    "amendement_uid": "AMDT-1",
    "article": "Article 3 bis",
    "dispositif": "<p>Supprimer cet article.</p>",
    "expose_sommaire": "<p>Ces obligations complexifient la préparation des Jeux.</p>",
}


def _faux_openai(monkeypatch, reponse="Supprime l'article 3 bis. L'auteur vise à alléger les obligations.", erreur=None):
    """Remplace openai.OpenAI et mémorise les paramètres de chaque appel."""
    appels = []

    class FauxClient:
        def __init__(self, base_url=None, api_key=None, timeout=None):
            appels.append({"base_url": base_url, "api_key": api_key})
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=self._create))

        def _create(self, **kwargs):
            appels[-1]["messages"] = kwargs["messages"]
            if erreur:
                raise erreur
            message = types.SimpleNamespace(content=reponse)
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FauxClient))
    return appels


def test_resume_mode_local(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    appels = _faux_openai(monkeypatch)

    r = client.post("/api/v2/resumer", json={**PAYLOAD, "provider": "local", "llm_endpoint": "http://localhost:1234/v1"})

    assert r.status_code == 200
    assert r.json()["resume"].startswith("Supprime l'article 3 bis")
    assert appels[0]["base_url"] == "http://localhost:1234/v1"
    # HTML nettoyé avant l'envoi au modèle
    assert "<p>" not in appels[0]["messages"][1]["content"]


def test_resume_groq_demo_utilise_la_cle_serveur_et_force_groq(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "cle-serveur-factice")
    appels = _faux_openai(monkeypatch)

    r = client.post("/api/v2/resumer", json={**PAYLOAD, "provider": "groq_auto",
                                             "llm_endpoint": "https://site-pirate.example/v1", "api_key": "x"})

    assert r.status_code == 200
    assert appels[0]["base_url"] == "https://api.groq.com/openai/v1"
    assert appels[0]["api_key"] == "cle-serveur-factice"


def test_resume_ia_locale_refusee_sur_vercel(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    _faux_openai(monkeypatch)

    r = client.post("/api/v2/resumer", json={**PAYLOAD, "provider": "local", "llm_endpoint": "http://localhost:1234/v1"})

    assert r.status_code == 502
    assert "SSRF" in r.json()["detail"]


def test_resume_erreur_ne_divulgue_pas_la_cle(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    _faux_openai(monkeypatch, erreur=RuntimeError("boom avec cle-secrete-123"))

    r = client.post("/api/v2/resumer", json={**PAYLOAD, "provider": "groq", "api_key": "cle-secrete-123",
                                             "llm_endpoint": "https://api.groq.com/openai/v1"})

    assert r.status_code == 502
    assert "cle-secrete-123" not in r.text


def test_dispositif_vide_sans_appel_ia(monkeypatch):
    appels = _faux_openai(monkeypatch)

    assert moteur.resumer_amendement("   ") == "Dispositif non renseigné."
    assert appels == []


def test_groq_demo_sans_cle_serveur_message_explicite(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    appels = _faux_openai(monkeypatch)

    r = client.post("/api/v2/resumer", json={**PAYLOAD, "provider": "groq_auto"})

    assert r.status_code == 503
    assert "GROQ_API_KEY" in r.json()["detail"]
    assert appels == []
