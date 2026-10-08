"""
Unit Tests for Legal Ingestion Module & Vector Indexer
======================================================
Tests EUR-Lex SPARQL client, Légifrance API client, directive chunking,
embedding generation, and vector indexing into `eu_directives_index`.
"""

import sys
import os
import pytest

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.legal_ingestion.eurlex_client import EURLexClient
from src.services.legal_ingestion.legifrance_client import LegifranceClient
from src.services.legal_ingestion.vector_indexer import LegalVectorIndexer


# ──────────────────────────────────────────────────────────────────────────
# EUR-Lex API Client Tests
# ──────────────────────────────────────────────────────────────────────────

def test_eurlex_build_sparql_query():
    client = EURLexClient()
    celex_id = "32019L1937"
    query = client.build_sparql_query(celex_id)
    assert "32019L1937" in query
    assert "PREFIX cdm:" in query


def test_eurlex_fetch_directive_mock_fallback():
    client = EURLexClient()
    celex_id = "32019L1937"
    directive = client.fetch_directive_by_celex(celex_id, mock_fallback=True)

    assert directive["celex_id"] == "32019L1937"
    assert "title" in directive
    assert len(directive["recitals"]) >= 1
    assert len(directive["articles"]) >= 1
    assert directive["articles"][0]["article_id"] == "Article 1"


# ──────────────────────────────────────────────────────────────────────────
# Légifrance API Client Tests
# ──────────────────────────────────────────────────────────────────────────

def test_legifrance_fetch_article():
    client = LegifranceClient()
    article = client.fetch_article("L. 1121-1", code_name="Code du travail", mock_fallback=True)

    assert article["article_id"] == "L. 1121-1"
    assert article["code_name"] == "Code du travail"
    assert "Code du travail" in article["title"]
    assert len(article["content"]) > 0


def test_legifrance_search_code_articles():
    client = LegifranceClient()
    results = client.search_code_articles("représailles", code_name="Code du travail", limit=3, mock_fallback=True)

    assert isinstance(results, list)
    assert len(results) > 0
    assert "article_id" in results[0]
    assert "content" in results[0]


# ──────────────────────────────────────────────────────────────────────────
# Local Vector DB Indexing Pipeline Tests
# ──────────────────────────────────────────────────────────────────────────

def test_vector_indexer_chunking():
    indexer = LegalVectorIndexer()
    directive_mock = {
        "celex_id": "32019L1937",
        "title": "Directive Whistleblowers",
        "recitals": [
            {"number": 1, "text": "Considérant premier sur les lanceurs d'alerte."}
        ],
        "articles": [
            {"article_id": "Article 1", "title": "Objet", "content": "Règles de protection."},
            {"article_id": "Article 2", "title": "Champ d'application", "content": "Champ matériel et personnel."}
        ],
        "source": "EURLEX"
    }

    chunks = indexer.chunk_directive(directive_mock)
    assert len(chunks) == 3
    assert chunks[0]["type"] == "recital"
    assert chunks[0]["article_id"] == "Considérant 1"
    assert chunks[1]["type"] == "article"
    assert chunks[1]["article_id"] == "Article 1"


def test_vector_indexer_embedding_generation():
    indexer = LegalVectorIndexer(embedding_dim=256, force_fallback_embedder=True)
    text = "Protection des personnes qui signalent des violations du droit de l'Union."
    vec = indexer.generate_embedding(text)

    assert isinstance(vec, list)
    assert len(vec) == 256
    # Verify vector is L2 normalized
    norm = sum(x * x for x in vec) ** 0.5
    assert abs(norm - 1.0) < 1e-4


def test_vector_indexer_upsert_and_similarity_search():
    indexer = LegalVectorIndexer(collection_name="eu_directives_index", embedding_dim=128, force_fallback_embedder=True)
    directive_mock = {
        "celex_id": "32019L1937",
        "title": "Directive Protection Lanceurs d'alerte",
        "recitals": [
            {"number": 1, "text": "Considérant sur la protection de la liberté d'expression et d'information."}
        ],
        "articles": [
            {"article_id": "Article 1", "title": "Objet", "content": "Normes minimales pour la protection des lanceurs d'alerte."},
            {"article_id": "Article 2", "title": "Signalement interne", "content": "Procédure d'alerte interne dans les entreprises."}
        ],
        "source": "EURLEX"
    }

    indexed_count = indexer.index_directive(directive_mock)
    assert indexed_count == 3

    stats = indexer.get_collection_stats()
    assert stats["total_records"] == 3
    assert stats["collection_name"] == "eu_directives_index"

    # Search for similar content
    query = "protection des lanceurs d'alerte"
    results = indexer.search_similar(query, top_k=2)

    assert len(results) == 2
    assert "score" in results[0]
    assert results[0]["score"] > 0
    assert "lanceurs" in results[0]["text"].lower() or "protection" in results[0]["text"].lower()
