"""
tests/test_rag_store.py — Tests unitaires du Vector Store SQLite Persistant & Grounding Strict
==============================================================================================
Vérifie :
  1. L'ingestion de chunks et directives dans une base SQLite temporaire (`bourbon_rag.db`).
  2. La recherche par similarité cosinus (embeddings vectoriels) et le repli lexical BM25/TF-IDF.
  3. Le grounding strict anti-hallucination : retour explicite de
     `"Information non disponible dans les sources"` (`status == "no_source"`)
     lorsque la base est vide ou qu'aucun chunk n'atteint `min_score=0.45`.
  4. Les routes FastAPI `/api/v2/rag/status`, `/api/v2/rag/ingest` et `/api/v2/rag/query`.
"""

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.index import app
from api.services.rag_store import (
    STRICT_NO_SOURCE_MESSAGE,
    PersistentRAGStore,
    cosine_similarity,
    query_rag,
)


def test_rag_store_empty_returns_strict_no_source(tmp_path: Path):
    """Sur une base SQLite vide, query_rag doit retourner 'Information non disponible dans les sources'."""
    db_file = tmp_path / "empty_rag.db"
    store = PersistentRAGStore(db_path=db_file)

    assert store.count_chunks() == 0
    res = query_rag("Quelles sont les règles de l'article 40 ?", store=store)

    assert res["status"] == "no_source"
    assert res["answer"] == STRICT_NO_SOURCE_MESSAGE
    assert res["message"] == STRICT_NO_SOURCE_MESSAGE
    assert res["results"] == []


def test_rag_store_ingest_and_lexical_fallback_search(tmp_path: Path):
    """Vérifie l'ingestion SQLite et le repli lexical BM25/TF-IDF au-dessus et en-dessous du seuil 0.45."""
    db_file = tmp_path / "lexical_rag.db"
    store = PersistentRAGStore(db_path=db_file)

    inserted = store.ingest_documents([
        {
            "doc_id": "CONST-1958",
            "titre": "Constitution de 1958",
            "article_ref": "Article 40",
            "source_type": "regle_irrecevabilite",
            "chunk_text": (
                "Les propositions et amendements formulés par les membres du Parlement ne sont pas recevables "
                "lorsque leur adoption aurait pour conséquence soit une diminution des ressources publiques, "
                "soit la création ou l'aggravation d'une charge publique."
            ),
        },
        {
            "doc_id": "32019L1937",
            "titre": "Directive Lanceurs d'alerte",
            "article_ref": "Article 19",
            "source_type": "directive_ue",
            "chunk_text": (
                "Les États membres prennent les mesures nécessaires pour interdire toute forme de représailles "
                "envers les auteurs de signalement."
            ),
        },
    ])

    assert inserted == 2
    assert store.count_chunks() == 2

    # 1. Requête pertinente -> doit dépasser min_score=0.45 et citer la source exacte
    hit = query_rag("irrecevabilité diminution des ressources publiques charge publique article 40", min_score=0.45, store=store)
    assert hit["status"] == "ok"
    assert len(hit["results"]) >= 1
    assert hit["results"][0]["doc_id"] == "CONST-1958"
    assert hit["results"][0]["article_ref"] == "Article 40"
    assert hit["results"][0]["score"] >= 0.45
    assert "[CONST-1958 · Article 40]" in hit["answer"]

    # 2. Requête hors-sujet -> aucun chunk >= 0.45 -> réponse stricte obligatoire
    miss = query_rag("exploration spatiale sur la planète Mars et propulsion nucléaire", min_score=0.45, store=store)
    assert miss["status"] == "no_source"
    assert miss["answer"] == STRICT_NO_SOURCE_MESSAGE
    assert miss["results"] == []


def test_rag_store_vector_cosine_similarity(tmp_path: Path, monkeypatch):
    """Vérifie le calcul de similarité cosinus lorsque des vecteurs d'embeddings locaux sont présents."""
    db_file = tmp_path / "vector_rag.db"
    store = PersistentRAGStore(db_path=db_file)

    assert abs(cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) - 1.0) < 1e-6
    assert abs(cosine_similarity([1.0, 0.0, 0.0], [0.0, 1.0, 0.0]) - 0.0) < 1e-6

    store.ingest_chunk(
        doc_id="DOC-VEC-1",
        titre="Directive Test Vectoriel",
        article_ref="Article 1",
        source_type="directive_ue",
        chunk_text="Texte technique encadrant les réseaux électriques.",
        embedding=[0.9, 0.1, 0.0],
    )
    store.ingest_chunk(
        doc_id="DOC-VEC-2",
        titre="Autre Directive",
        article_ref="Article 2",
        source_type="directive_ue",
        chunk_text="Dispositions relatives à la pêche maritime.",
        embedding=[0.0, 0.1, 0.9],
    )

    # Simule un serveur d'embeddings local retournant un vecteur proche de DOC-VEC-1
    monkeypatch.setattr(store, "fetch_local_embedding", lambda text, timeout=2.0: [0.95, 0.05, 0.0])

    res = store.query_rag("question sémantique", top_k=1, min_score=0.80, try_remote_embedding=True)
    assert res["status"] == "ok"
    assert len(res["results"]) == 1
    assert res["results"][0]["doc_id"] == "DOC-VEC-1"
    assert res["results"][0]["score"] >= 0.95


def test_rag_fastapi_endpoints(tmp_path: Path, monkeypatch):
    """Vérifie les endpoints REST /api/v2/rag/status, /api/v2/rag/ingest et /api/v2/rag/query."""
    import api.services.rag_store as rs

    temp_store = PersistentRAGStore(db_path=tmp_path / "api_rag.db")
    temp_store.seed_default_corpus()
    monkeypatch.setattr(rs, "_DEFAULT_STORE", temp_store)

    client = TestClient(app)

    status_res = client.get("/api/v2/rag/status")
    assert status_res.status_code == 200
    assert status_res.json()["total_chunks"] >= 5

    ingest_res = client.post(
        "/api/v2/rag/ingest",
        json={
            "documents": [
                {
                    "doc_id": "REGLE-IRR-101",
                    "titre": "Jurisprudence Commission des Finances",
                    "article_ref": "Règle 101",
                    "source_type": "regle_irrecevabilite",
                    "chunk_text": "Un gage financier portant sur les tabacs ne peut compenser une création de dépense directe.",
                }
            ]
        },
    )
    assert ingest_res.status_code == 200
    assert ingest_res.json()["inserted_chunks"] == 1

    query_ok = client.post(
        "/api/v2/rag/query",
        json={"question": "gage financier tabacs création de dépense", "min_score": 0.45},
    )
    assert query_ok.status_code == 200
    assert query_ok.json()["status"] == "ok"
    assert query_ok.json()["results"][0]["doc_id"] == "REGLE-IRR-101"

    query_miss = client.post(
        "/api/v2/rag/query",
        json={"question": "recette traditionnelle du cassoulet toulousain", "min_score": 0.45},
    )
    assert query_miss.status_code == 200
    assert query_miss.json()["status"] == "no_source"
    assert query_miss.json()["answer"] == STRICT_NO_SOURCE_MESSAGE
