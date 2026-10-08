"""
Surtransposition & EU Compliance Analysis Engine
================================================
Performs local RAG evaluation comparing French draft amendments against EU Directive
baselines retrieved from `eu_directives_index` vector store.
100% Air-Gapped execution preserving confidentiality of draft legislative texts.
"""

from __future__ import annotations
import os
import re
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
import requests
from pydantic import BaseModel, Field, ValidationError

from src.services.legal_ingestion.vector_indexer import LegalVectorIndexer

logger = logging.getLogger("bourbon.surtransposition")

OLLAMA_DEFAULT_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "mistral"


class SurtranspositionStatus(str, Enum):
    STRICT_TRANSPOSITION = "STRICT_TRANSPOSITION"
    NATIONAL_ADDITION = "NATIONAL_ADDITION"
    SURTRANSPOSITION_ALERT = "SURTRANSPOSITION_ALERT"


class MatchedSource(BaseModel):
    celex_id: str = Field(..., description="Identifiant CELEX de la directive européenne")
    article_id: str = Field(..., description="Numéro d'article ou considérant")
    title: str = Field("", description="Titre ou intitulé de la source")
    score: float = Field(0.0, description="Score de similitude vectorielle (0.0 à 1.0)")
    text_snippet: str = Field("", description="Extrait du texte de la directive")


class SurtranspositionAnalysisResult(BaseModel):
    status: Literal["STRICT_TRANSPOSITION", "NATIONAL_ADDITION", "SURTRANSPOSITION_ALERT"] = Field(
        ...,
        description="Résultat de l'analyse de surtransposition"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Niveau de confiance de l'analyse (0.0 à 1.0)"
    )
    delta_summary: str = Field(
        ...,
        description="Explication synthétique des écarts ou sur-exigences nationales"
    )
    matched_sources: List[MatchedSource] = Field(
        default_factory=list,
        description="Sources européennes de référence extraites du RAG local"
    )
    target_article: Optional[str] = Field(
        None,
        description="Article de loi national ou amendement visé"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="Horodatage ISO de l'analyse"
    )
    analysis_mode: str = Field(
        "RAG_LLM",
        description="Mode d'analyse appliqué (RAG_LLM ou RAG_HEURISTIC_FALLBACK)"
    )


class SurtranspositionChecker:
    """
    RAG & LLM Analysis engine evaluating draft amendments against EU Directive baselines.
    """

    def __init__(
        self,
        vector_indexer: Optional[LegalVectorIndexer] = None,
        ollama_url: Optional[str] = None,
        model_name: str = DEFAULT_MODEL
    ):
        self.vector_indexer = vector_indexer or LegalVectorIndexer()
        self.ollama_url = ollama_url or os.getenv("OLLAMA_URL", OLLAMA_DEFAULT_URL)
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)

    def analyze_amendment(
        self,
        amendment_text: str,
        target_article: Optional[str] = None,
        celex_id: Optional[str] = None,
        top_k: int = 3,
        timeout: int = 12
    ) -> SurtranspositionAnalysisResult:
        """
        Core RAG evaluation function:
        1. Query `eu_directives_index` vector DB for top-k matching directive chunks.
        2. Execute local LLM prompt expecting strict JSON output.
        3. Parse output into Pydantic model with deterministic fallback on network failure or invalid JSON.
        """
        clean_text = amendment_text.strip()
        if not clean_text:
            return SurtranspositionAnalysisResult(
                status="STRICT_TRANSPOSITION",
                confidence=0.5,
                delta_summary="Texte d'amendement vide.",
                matched_sources=[],
                target_article=target_article,
                analysis_mode="EMPTY_INPUT_FALLBACK"
            )

        # 1. RAG Retrieval from local vector DB
        retrieved_chunks = self.vector_indexer.search_similar(
            query=clean_text,
            collection_name="eu_directives_index",
            top_k=top_k
        )

        matched_sources: List[MatchedSource] = [
            MatchedSource(
                celex_id=c.get("metadata", {}).get("celex_id", celex_id or "N/A"),
                article_id=c.get("metadata", {}).get("article_id", "Art."),
                title=c.get("metadata", {}).get("title", ""),
                score=c.get("score", 0.0),
                text_snippet=c.get("text", "")[:300]
            )
            for c in retrieved_chunks
        ]

        # 2. Local LLM Evaluation
        try:
            llm_response = self._call_local_llm(
                amendment_text=clean_text,
                matched_sources=matched_sources,
                target_article=target_article,
                timeout=timeout
            )
            if llm_response:
                parsed_result = self._parse_llm_json(llm_response, matched_sources, target_article)
                if parsed_result:
                    return parsed_result
        except Exception as err:
            logger.warning(f"Local LLM surtransposition check failed: {err}")

        # 3. Deterministic Heuristic Fallback (Resilient Air-Gapped Processing)
        return self._heuristic_fallback_analysis(
            amendment_text=clean_text,
            matched_sources=matched_sources,
            target_article=target_article
        )

    def _format_prompt(
        self,
        amendment_text: str,
        matched_sources: List[MatchedSource],
        target_article: Optional[str]
    ) -> str:
        """Construct structured prompt enforcing strict JSON output format."""
        sources_context = "\n".join([
            f"- [{s.celex_id} | {s.article_id}] {s.text_snippet}"
            for s in matched_sources
        ]) if matched_sources else "Aucune source européenne directe trouvée dans l'index local."

        target_info = f"visant {target_article}" if target_article else ""

        prompt = f"""
Tu es un expert en droit européen et légistique française.
Analyse l'amendement parlementaire suivant {target_info} au regard des normes de la Directive Européenne de référence ci-dessous.

RÈGLES D'ÉVALUATION DE SURTRANSPOSITION :
1. "STRICT_TRANSPOSITION" : L'amendement reprend exactement les exigences ou le socle de la directive sans ajouter de contrainte nationale excessive.
2. "NATIONAL_ADDITION" : L'amendement précise une modalité d'application nationale légitime sans créer de distorsion majeure.
3. "SURTRANSPOSITION_ALERT" : L'amendement impose des délais plus stricts, des sanctions plus lourdes, des seuils plus bas ou des obligations additionnelles non requises par le droit européen.

TEXTE DE L'AMENDEMENT PARLEMENTAIRE :
\"\"\"
{amendment_text[:1500]}
\"\"\"

SOURCES DIRECTIVE EUROPÉENNE EXTRAITES DU RAG :
{sources_context}

FORMAT DE RÉPONSE EXIGÉ :
Réponds EXCLUSIVEMENT par un objet JSON valide suivant exactement cette structure :
{{
  "status": "STRICT_TRANSPOSITION" | "NATIONAL_ADDITION" | "SURTRANSPOSITION_ALERT",
  "confidence": 0.85,
  "delta_summary": "Explication claire et synthétique des écarts juridiques constatés."
}}
"""
        return prompt.strip()

    def _call_local_llm(
        self,
        amendment_text: str,
        matched_sources: List[MatchedSource],
        target_article: Optional[str],
        timeout: int = 12
    ) -> Optional[str]:
        """Call local Ollama endpoint synchronously."""
        prompt = self._format_prompt(amendment_text, matched_sources, target_article)
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9
            }
        }
        res = requests.post(self.ollama_url, json=payload, timeout=timeout)
        if res.status_code == 200:
            data = res.json()
            return data.get("response", "")
        return None

    def _parse_llm_json(
        self,
        raw_llm_text: str,
        matched_sources: List[MatchedSource],
        target_article: Optional[str]
    ) -> Optional[SurtranspositionAnalysisResult]:
        """Extract and validate JSON response with Pydantic."""
        json_match = re.search(r"\{.*\}", raw_llm_text, re.DOTALL)
        if not json_match:
            return None

        json_str = json_match.group(0)
        try:
            data = json.loads(json_str)
            # Ensure status maps to allowed Literal
            raw_status = str(data.get("status", "")).upper()
            if raw_status not in ["STRICT_TRANSPOSITION", "NATIONAL_ADDITION", "SURTRANSPOSITION_ALERT"]:
                raw_status = "NATIONAL_ADDITION"

            confidence_val = float(data.get("confidence", 0.8))
            confidence_val = max(0.0, min(1.0, confidence_val))

            return SurtranspositionAnalysisResult(
                status=raw_status,  # type: ignore
                confidence=confidence_val,
                delta_summary=str(data.get("delta_summary", "Analyse effectuée via LLM local.")),
                matched_sources=matched_sources,
                target_article=target_article,
                analysis_mode="RAG_LLM"
            )
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            logger.warning(f"Failed to parse LLM JSON output: {e}")
            return None

    def _heuristic_fallback_analysis(
        self,
        amendment_text: str,
        matched_sources: List[MatchedSource],
        target_article: Optional[str]
    ) -> SurtranspositionAnalysisResult:
        """
        Deterministic rule-based keyword analysis when local LLM is unreachable/offline.
        Guarantees strict compliance evaluation without unhandled exceptions.
        """
        text_lower = amendment_text.lower()
        
        # Keywords indicating surtransposition signals (stricter deadlines, heavy sanctions, lower thresholds)
        surtransposition_triggers = [
            "sanction pénale", "amende de 5", "délai de 15 jours", "interdiction totale",
            "obligation supplémentaire", "doublement", "peine d'emprisonnement",
            "délai réduit", "seuil de 10"
        ]

        addition_triggers = [
            "modalité", "rapport annuel", "décret en conseil d'état", "préciser",
            "comité de suivi", "registre national"
        ]

        if any(trigger in text_lower for trigger in surtransposition_triggers):
            status = "SURTRANSPOSITION_ALERT"
            summary = "Détection d'obligations renforcées, de sanctions accrues ou de délais resserrés par rapport au socle européen."
            confidence = 0.85
        elif any(trigger in text_lower for trigger in addition_triggers):
            status = "NATIONAL_ADDITION"
            summary = "Précision de modalités administratives nationales sans altération de la portée de la directive."
            confidence = 0.80
        else:
            status = "STRICT_TRANSPOSITION"
            summary = "Dispositions alignées sur le socle minimal de la directive de référence."
            confidence = 0.75

        return SurtranspositionAnalysisResult(
            status=status,
            confidence=confidence,
            delta_summary=summary,
            matched_sources=matched_sources,
            target_article=target_article,
            analysis_mode="RAG_HEURISTIC_FALLBACK"
        )
