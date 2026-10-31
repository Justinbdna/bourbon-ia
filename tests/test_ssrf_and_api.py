"""
Tests unitaires pour la protection SSRF et la route /api/v2/surtransposition
=============================================================================
Valide le blindage SSRF en environnement Cloud/Vercel et l'exposition
de l'analyse de surtransposition UE.
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient

# Ensure workspace root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.llm_semantic_engine import validate_endpoint_url, sanitize_log_message
from api.index import app
from api.deterministic_engine import qualify_irrecevabilite
from api.schemas import EnrichedAmendment


# ──────────────────────────────────────────────────────────────────────────
# 1. Tests de Protection Anti-SSRF
# ──────────────────────────────────────────────────────────────────────────

def test_validate_endpoint_url_local_env(monkeypatch):
    """En environnement local (VERCEL != '1'), localhost et les IP privées sont autorisées."""
    monkeypatch.delenv("VERCEL", raising=False)

    url_local = "http://localhost:1234/v1"
    assert validate_endpoint_url(url_local) == url_local

    url_ip = "http://127.0.0.1:11434/v1"
    assert validate_endpoint_url(url_ip) == url_ip


def test_validate_endpoint_url_cloud_blocks_localhost_and_metadata(monkeypatch):
    """En environnement Cloud (VERCEL == '1'), tout accès loopback, métadonnées ou IP privée est bloqué."""
    monkeypatch.setenv("VERCEL", "1")

    # Localhost
    with pytest.raises(ValueError, match="Accès aux hôtes locaux interdit"):
        validate_endpoint_url("http://localhost:1234/v1")

    with pytest.raises(ValueError, match="Accès aux hôtes locaux interdit"):
        validate_endpoint_url("http://127.0.0.1:8000/v1")

    # Métadonnées AWS / GCP / Azure
    with pytest.raises(ValueError, match="Accès aux réseaux privés et métadonnées interdit"):
        validate_endpoint_url("http://169.254.169.254/latest/meta-data/")

    # Plages privées RFC 1918
    with pytest.raises(ValueError, match="Accès aux réseaux privés et métadonnées interdit"):
        validate_endpoint_url("http://10.0.1.5:8000/v1")

    with pytest.raises(ValueError, match="Accès aux réseaux privés et métadonnées interdit"):
        validate_endpoint_url("http://192.168.1.100:1234/v1")

    # FQDN public autorisé
    public_url = "https://api.groq.com/openai/v1"
    assert validate_endpoint_url(public_url) == public_url


def test_validate_endpoint_url_invalid_scheme():
    """Les schémas non http/https (ex: file://, gopher://, ftp://) sont strictement rejetés."""
    with pytest.raises(ValueError, match="Protocole non sécurisé"):
        validate_endpoint_url("file:///etc/passwd")

    with pytest.raises(ValueError, match="Protocole non sécurisé"):
        validate_endpoint_url("gopher://internal:70")


def test_sanitize_log_message_redacts_keys():
    """Masquage rigoureux des clés d'API secrètes."""
    secret_key = "gsk_abcd1234efgh5678ijkl9012mnop3456"
    raw_log = f"Error calling endpoint with key {secret_key} and Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    sanitized = sanitize_log_message(raw_log, secret_key)

    assert secret_key not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized
    assert "Bearer [REDACTED]" in sanitized


# ──────────────────────────────────────────────────────────────────────────
# 2. Tests de Qualification Fine des Irrecevabilités (Art. 40 vs Art. 45/98)
# ──────────────────────────────────────────────────────────────────────────

def test_qualify_irrecevabilite_art40():
    """Détection explicite de l'irrecevabilité financière (Article 40)."""
    amend = EnrichedAmendment(
        amendement_uid="AM-IRR-40",
        dispositif_raw="Cet amendement entraîne une charge financière nouvelle.",
        raw_dict={"cycleDeVie": {"etatChronologique": {"code": "IRR40", "mention": "Irrecevable Art. 40"}}},
    )
    qualif = qualify_irrecevabilite(amend)
    assert qualif == "Irrecevable (Art. 40 - Recevabilité financière)"


def test_qualify_irrecevabilite_art45():
    """Détection explicite du cavalier législatif (Article 45 / 98)."""
    amend = EnrichedAmendment(
        amendement_uid="AM-IRR-45",
        dispositif_raw="Dispositif sans lien indirect avec le texte.",
        raw_dict={"corps": {"cartoucheInformatif": "Irrecevable au titre de l'article 45 de la Constitution (cavalier législatif)"}},
    )
    qualif = qualify_irrecevabilite(amend)
    assert qualif == "Irrecevable (Art. 45/98 - Cavalier législatif / Entonnoir)"


# ──────────────────────────────────────────────────────────────────────────
# 3. Tests de la Route API /api/v2/surtransposition
# ──────────────────────────────────────────────────────────────────────────

def test_api_v2_surtransposition_endpoint():
    """La route /api/v2/surtransposition analyse et retourne un verdict conforme."""
    client = TestClient(app)

    payload = {
        "amendement_uid": "AM-TEST-UE-01",
        "dispositif": "Les entreprises doivent réaliser un rapport annuel et obtenir une certification obligatoire d'un organisme agréé.",
        "expose_sommaire": "Transposition de la directive sur les marchés publics avec exigences renforcées.",
        "article_vise": "Article 11",
    }

    response = client.post("/api/v2/surtransposition", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert data["status"] in ("STRICT_TRANSPOSITION", "NATIONAL_ADDITION", "SURTRANSPOSITION_ALERT")
    assert "confidence" in data
    assert 0.0 <= data["confidence"] <= 1.0
    assert "delta_summary" in data
    assert "matched_sources" in data
    assert data.get("amendement_uid") == "AM-TEST-UE-01"


def test_api_v2_surtransposition_batch():
    """La route /api/v2/surtransposition accepte une liste d'amendements."""
    client = TestClient(app)

    payload = {
        "amendements": [
            {
                "id": "AM-UE-1",
                "dispositif": "Les projets énumérés font l'objet d'une évaluation.",
                "article": "Article 5",
            },
            {
                "id": "AM-UE-2",
                "dispositif": "Les sanctions pénales sont portées à 5 ans d'emprisonnement et 500 000 euros d'amende.",
                "article": "Article 8",
            },
        ]
    }

    response = client.post("/api/v2/surtransposition", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["amendement_uid"] == "AM-UE-1"
    assert data[1]["amendement_uid"] == "AM-UE-2"
