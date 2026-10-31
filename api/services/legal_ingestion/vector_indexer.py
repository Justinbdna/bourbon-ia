"""
Local Vector DB Indexing Pipeline for EU Directives & National Legal Baseline
=============================================================================
Handles text chunking, local embeddings (sentence-transformers / BAAI/bge-m3 / fallback),
and vector storage in local collection `eu_directives_index`.
Strictly air-gapped and Privacy-Preserving.
"""

from __future__ import annotations
import math
import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Attempt importing sentence_transformers for production embedding
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    SentenceTransformer = None
    HAS_SENTENCE_TRANSFORMERS = False


class LegalVectorIndexer:
    """
    Local Vector Indexer for chunking, embedding, and storing EU Directive recitals,
    articles, and national legal baseline texts into `eu_directives_index`.
    """

    def __init__(
        self,
        collection_name: str = "eu_directives_index",
        model_name: str = "BAAI/bge-m3",
        embedding_dim: int = 1024,
        force_fallback_embedder: bool = False
    ):
        self.collection_name = collection_name
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        self.force_fallback = force_fallback_embedder
        self._transformer_model = None

        # Local in-memory vector store table
        # Structure: { collection_name: [ { "id": str, "vector": List[float], "metadata": dict, "text": str } ] }
        self.collections: Dict[str, List[Dict[str, Any]]] = {
            self.collection_name: []
        }

        if HAS_SENTENCE_TRANSFORMERS and not self.force_fallback:
            try:
                self._transformer_model = SentenceTransformer(self.model_name)
            except Exception as e:
                logger.warning(f"Could not load SentenceTransformer '{self.model_name}': {e}. Using deterministic local embedder.")

    def generate_embedding(self, text: str) -> List[float]:
        """Generate a dense vector embedding for text using local model or deterministic fallback."""
        if self._transformer_model is not None:
            try:
                vector = self._transformer_model.encode(text, convert_to_numpy=True).tolist()
                return vector
            except Exception as e:
                logger.warning(f"Error during model encoding: {e}. Falling back.")

        # Deterministic air-gapped L2-normalized embedding (dim-dimensional vector)
        return self._deterministic_local_embedding(text, self.embedding_dim)

    def _deterministic_local_embedding(self, text: str, dim: int = 1024) -> List[float]:
        """
        Generates a normalized L2 dense float vector from input text string using SHA-512 hashing seeds.
        Provides zero-dependency, reproducible embedding similarity for offline unit tests & local dev.
        """
        tokens = text.lower().split()
        vector = [0.0] * dim

        if not tokens:
            return vector

        for token in tokens:
            # Hash token to produce deterministic pseudo-random dimensions
            h = hashlib.sha512(token.encode("utf-8")).digest()
            for i in range(min(16, dim)):
                byte_val = h[i]
                dim_idx = (h[i + 16] * 256 + h[i + 32]) % dim
                weight = (byte_val - 128) / 128.0
                vector[dim_idx] += weight

        # Normalize vector to unit length (L2 norm)
        norm = math.sqrt(sum(val * val for val in vector))
        if norm > 0:
            vector = [val / norm for val in vector]

        return vector

    def chunk_directive(self, directive_data: Dict[str, Any], max_chunk_size: int = 500) -> List[Dict[str, Any]]:
        """
        Splits a directive's recitals and articles into structured indexable chunks with metadata.
        """
        celex_id = directive_data.get("celex_id", "UNKNOWN_CELEX")
        title = directive_data.get("title", "")
        chunks = []

        # 1. Chunk Recitals
        for recital in directive_data.get("recitals", []):
            rec_num = recital.get("number", "")
            rec_text = recital.get("text", "").strip()
            if rec_text:
                chunks.append({
                    "chunk_id": f"{celex_id}_recital_{rec_num}",
                    "celex_id": celex_id,
                    "type": "recital",
                    "article_id": f"Considérant {rec_num}",
                    "title": f"Considérant {rec_num} - {title}",
                    "text": rec_text,
                    "source": directive_data.get("source", "EURLEX")
                })

        # 2. Chunk Articles
        for article in directive_data.get("articles", []):
            art_id = article.get("article_id", "Art.")
            art_title = article.get("title", "")
            art_content = article.get("content", "").strip()

            if len(art_content) <= max_chunk_size:
                chunks.append({
                    "chunk_id": f"{celex_id}_{art_id.replace(' ', '_')}",
                    "celex_id": celex_id,
                    "type": "article",
                    "article_id": art_id,
                    "title": f"{art_id} ({art_title})",
                    "text": f"{art_title}\n{art_content}".strip(),
                    "source": directive_data.get("source", "EURLEX")
                })
            else:
                # Sub-chunk long articles into paragraphs
                paragraphs = [p.strip() for p in art_content.split("\n\n") if p.strip()]
                for idx, para in enumerate(paragraphs, 1):
                    chunks.append({
                        "chunk_id": f"{celex_id}_{art_id.replace(' ', '_')}_p{idx}",
                        "celex_id": celex_id,
                        "type": "article",
                        "article_id": art_id,
                        "title": f"{art_id} (Partie {idx})",
                        "text": f"{art_title}\n{para}".strip(),
                        "source": directive_data.get("source", "EURLEX")
                    })

        return chunks

    def index_directive(
        self,
        directive_data: Dict[str, Any],
        target_collection: Optional[str] = None
    ) -> int:
        """
        Chunks directive text, computes embeddings, and upserts entries into vector collection.
        Returns the number of chunks indexed.
        """
        col_name = target_collection or self.collection_name
        if col_name not in self.collections:
            self.collections[col_name] = []

        chunks = self.chunk_directive(directive_data)
        count = 0

        for chunk in chunks:
            vector = self.generate_embedding(chunk["text"])
            entry = {
                "id": chunk["chunk_id"],
                "vector": vector,
                "text": chunk["text"],
                "metadata": {
                    "celex_id": chunk["celex_id"],
                    "type": chunk["type"],
                    "article_id": chunk["article_id"],
                    "title": chunk["title"],
                    "source": chunk["source"]
                }
            }
            
            # Upsert into collection (update if existing ID, else insert)
            existing_idx = next(
                (i for i, item in enumerate(self.collections[col_name]) if item["id"] == entry["id"]),
                None
            )
            if existing_idx is not None:
                self.collections[col_name][existing_idx] = entry
            else:
                self.collections[col_name].append(entry)
            
            count += 1

        return count

    def search_similar(
        self,
        query: str,
        collection_name: Optional[str] = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Perform cosine similarity search over vector collection given a text query.
        """
        col_name = collection_name or self.collection_name
        items = self.collections.get(col_name, [])

        if not items or not query.strip():
            return []

        query_vec = self.generate_embedding(query)

        results: List[Tuple[float, Dict[str, Any]]] = []
        for item in items:
            score = self._cosine_similarity(query_vec, item["vector"])
            results.append((
                score,
                {
                    "id": item["id"],
                    "score": round(score, 4),
                    "text": item["text"],
                    "metadata": item["metadata"]
                }
            ))

        # Sort descending by similarity score
        results.sort(key=lambda x: x[0], reverse=True)
        return [res[1] for res in results[:top_k]]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two float vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = math.sqrt(sum(a * a for a in vec1))
        norm_b = math.sqrt(sum(b * b for b in vec2))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def get_collection_stats(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """Return total document count and vector specs for a collection."""
        col_name = collection_name or self.collection_name
        items = self.collections.get(col_name, [])
        return {
            "collection_name": col_name,
            "total_records": len(items),
            "embedding_dim": len(items[0]["vector"]) if items else self.embedding_dim,
            "model_name": self.model_name
        }
