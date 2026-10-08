"""
Legal Ingestion Service Module for Bourbon.IA
=============================================
Provides client connectors for EUR-Lex (CELLAR SPARQL), Légifrance (PISTE API),
and local vector indexing for EU Directives & National Legal Baselines.
"""

from .eurlex_client import EURLexClient
from .legifrance_client import LegifranceClient
from .vector_indexer import LegalVectorIndexer

__all__ = ["EURLexClient", "LegifranceClient", "LegalVectorIndexer"]
