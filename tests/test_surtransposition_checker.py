"""
Unit Tests for Surtransposition & Compliance Analysis Engine
============================================================
Tests Pydantic validation, RAG vector retrieval integration, local LLM parsing,
and deterministic fallback mechanisms.
"""

import sys
import os
import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.legal_ingestion.vector_indexer import LegalVectorIndexer
from src.services.analysis.surtransposition_checker import (
    SurtranspositionChecker,
    SurtranspositionAnalysisResult,
    SurtranspositionStatus,
    MatchedSource
)


def test_surtransposition_result_pydantic_validation():
    # Valid Pydantic model creation
    result = SurtranspositionAnalysisResult(
        status="SURTRANSPOSITION_ALERT",
        confidence=0.9,
        delta_summary="Sanction pénale nationale non prévue par la directive.",
        matched_sources=[
            MatchedSource(
                celex_id="32019L1937",
                article_id="Article 3",
                title="Interdiction des représailles",
                score=0.88,
                text_snippet="Toute forme de représailles est interdite."
            )
        ],
        target_article="Article 11"
    )

    assert result.status == "SURTRANSPOSITION_ALERT"
    assert result.confidence == 0.9
    assert len(result.matched_sources) == 1
    assert result.matched_sources[0].celex_id == "32019L1937"


def test_surtransposition_result_invalid_confidence_raises():
    with pytest.raises(ValidationError):
        SurtranspositionAnalysisResult(
            status="STRICT_TRANSPOSITION",
            confidence=1.5,  # Invalid: > 1.0
            delta_summary="Test invalid confidence"
        )


def test_surtransposition_checker_heuristic_alert():
    checker = SurtranspositionChecker()
    amendment_text = "Le présent amendement prévoit une amende de 5 millions d'euros et une sanction pénale renforcée."
    res = checker.analyze_amendment(amendment_text, target_article="Article 4")

    assert res.status == "SURTRANSPOSITION_ALERT"
    assert res.confidence >= 0.8
    assert "sanction" in res.delta_summary.lower() or "renforcée" in res.delta_summary.lower()
    assert res.target_article == "Article 4"


def test_surtransposition_checker_heuristic_addition():
    checker = SurtranspositionChecker()
    amendment_text = "Un décret en conseil d'état précise les modalités d'application du comité de suivi."
    res = checker.analyze_amendment(amendment_text, target_article="Article 2")

    assert res.status == "NATIONAL_ADDITION"
    assert res.confidence >= 0.75


def test_surtransposition_checker_rag_integration():
    # Setup vector indexer with mock directive content
    indexer = LegalVectorIndexer(collection_name="eu_directives_index", embedding_dim=128, force_fallback_embedder=True)
    indexer.index_directive({
        "celex_id": "32019L1937",
        "title": "Directive Whistleblowers",
        "articles": [
            {
                "article_id": "Article 3",
                "title": "Interdiction des représailles",
                "content": "Interdiction de toute mesure de représailles directe ou indirecte."
            }
        ]
    })

    checker = SurtranspositionChecker(vector_indexer=indexer)
    amendment = "Interdiction des mesures de représailles envers les signalants."
    res = checker.analyze_amendment(amendment, celex_id="32019L1937")

    assert len(res.matched_sources) > 0
    assert res.matched_sources[0].celex_id == "32019L1937"
    assert res.matched_sources[0].article_id == "Article 3"


def test_surtransposition_checker_llm_json_parsing():
    checker = SurtranspositionChecker()
    raw_llm_output = """
    Voici mon analyse :
    ```json
    {
      "status": "SURTRANSPOSITION_ALERT",
      "confidence": 0.92,
      "delta_summary": "Délai de notification réduit à 15 jours au lieu du délai européen de 3 mois."
    }
    ```
    """
    sources = [
        MatchedSource(celex_id="32019L1937", article_id="Article 9", score=0.85)
    ]
    parsed = checker._parse_llm_json(raw_llm_output, sources, target_article="Article 5")

    assert parsed is not None
    assert parsed.status == "SURTRANSPOSITION_ALERT"
    assert parsed.confidence == 0.92
    assert "15 jours" in parsed.delta_summary
    assert parsed.target_article == "Article 5"
    assert parsed.analysis_mode == "RAG_LLM"
