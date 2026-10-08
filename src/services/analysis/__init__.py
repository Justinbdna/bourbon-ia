"""
Surtransposition & EU Compliance Analysis Service
=================================================
Local RAG and LLM-driven compliance checking for draft amendments.
"""

from .surtransposition_checker import (
    SurtranspositionChecker,
    SurtranspositionAnalysisResult,
    SurtranspositionStatus,
    MatchedSource
)

__all__ = [
    "SurtranspositionChecker",
    "SurtranspositionAnalysisResult",
    "SurtranspositionStatus",
    "MatchedSource"
]
