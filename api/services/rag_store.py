"""
api/services/rag_store.py — Vector Store SQLite Persistant & Grounding Strict Bourbon.IA
========================================================================================
Architecture 100 % souveraine et légère (sans dépendance lourde type PyTorch/Transformers) :
  - Stockage persistant dans SQLite (`data/bourbon_rag.db`) avec colonnes :
    `doc_id`, `titre`, `article_ref`, `source_type`, `chunk_text`, `embedding_json`, `updated_at`.
  - Génération d'embeddings locaux via l'API compatible OpenAI `/v1/embeddings`
    (LM Studio `text-embedding-nomic-embed-text-v1.5` ou Ollama `bge-m3`), avec calcul
    de similarité cosinus vectorisée en Python/NumPy pur.
  - Repli lexical hybride BM25 / TF-IDF si aucun serveur d'embeddings n'est démarré.
  - Tolérance zéro pour les hallucinations : si la base est vide ou qu'aucun passage
    ne dépasse `min_score` (0.45 par défaut), retourne le statut `no_source` et la
    réponse stricte `"Information non disponible dans les sources"`.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import sqlite3
import tempfile
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

try:
    from api.llm_semantic_engine import validate_endpoint_url
except ModuleNotFoundError:
    from llm_semantic_engine import validate_endpoint_url

logger = logging.getLogger("bourbon.rag_store")

STRICT_NO_SOURCE_MESSAGE = "Information non disponible dans les sources"

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = WORKSPACE_ROOT / "data" / "bourbon_rag.db"


def _resolve_tmp_fallback_path() -> Path:
    """Retourne `/tmp/bourbon_rag.db` sur POSIX (Vercel/Linux/macOS) ou le dossier temp OS sous Windows."""
    posix_tmp = Path("/tmp")
    if os.name != "nt" or posix_tmp.exists():
        return posix_tmp / "bourbon_rag.db"
    return Path(tempfile.gettempdir()) / "bourbon_rag.db"


VERCEL_FALLBACK_DB_PATH = _resolve_tmp_fallback_path()


def resolve_sqlite_db_path(default_path: str | Path = "data/bourbon_rag.db") -> Path:
    """
    Résout le chemin SQLite accessible en écriture pour Bourbon.IA :
      1. Si `BOURBON_DB_PATH` (ou `BOURBON_RAG_DB_PATH`) est défini dans l'environnement, l'utiliser.
      2. Sinon, si `VERCEL` est présent dans l'environnement ou si le dossier parent
         de `default_path` n'est pas accessible en écriture, basculer sur `/tmp/bourbon_rag.db`
         (ou le répertoire temporaire OS sous Windows).
    """
    env_path = os.environ.get("BOURBON_DB_PATH") or os.environ.get("BOURBON_RAG_DB_PATH")
    if env_path and env_path.strip():
        candidate = Path(env_path.strip())
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            if os.access(candidate.parent, os.W_OK):
                return candidate
        except OSError:
            return VERCEL_FALLBACK_DB_PATH

    if os.environ.get("VERCEL"):
        try:
            VERCEL_FALLBACK_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        return VERCEL_FALLBACK_DB_PATH

    if str(default_path) == "data/bourbon_rag.db":
        candidate = DEFAULT_DB_PATH
    else:
        candidate = Path(default_path)

    try:
        candidate.parent.mkdir(parents=True, exist_ok=True)
        if not os.access(candidate.parent, os.W_OK):
            return VERCEL_FALLBACK_DB_PATH
        if candidate.exists() and not os.access(candidate, os.W_OK):
            return VERCEL_FALLBACK_DB_PATH
        return candidate
    except OSError:
        return VERCEL_FALLBACK_DB_PATH

DEFAULT_EMBEDDING_ENDPOINT = "http://localhost:1234/v1"
DEFAULT_EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"

_FRENCH_STOPWORDS = frozenset({
    "le", "la", "les", "de", "du", "des", "un", "une", "et", "ou", "en", "au", "aux",
    "ce", "cet", "cette", "ces", "dans", "sur", "pour", "par", "avec", "sans", "sous",
    "qui", "que", "quoi", "dont", "ou", "est", "sont", "etre", "avoir", "il", "elle",
    "on", "nous", "vous", "ils", "elles", "ne", "pas", "plus", "tout", "tous", "toute",
    "toutes", "son", "sa", "ses", "leur", "leurs", "mon", "ma", "mes", "ton", "ta", "tes",
    "notre", "votre", "meme", "memes", "comme", "mais", "donc", "or", "ni", "car", "si",
    "afin", "ainsi", "alors", "apres", "avant", "chez", "contre", "depuis", "entre",
    "vers", "tres", "peut", "peuvent", "doit", "doivent", "fait", "faire", "ete", "ai",
    "as", "avons", "avez", "ont", "sera", "seront", "soit", "soient", "quel", "quelle",
    "quels", "quelles", "comment", "pourquoi", "quand", "chaque", "aucun", "aucune",
})


def _strip_accents(text: str) -> str:
    norm = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in norm if unicodedata.category(ch) != "Mn")


def _tokenize_lexical(text: str) -> list[str]:
    """
    Découpe un texte en tokens lexicaux normalisés (sans accents, sans stopwords)
    et ajoute des radicaux (stems de 5 caractères) pour capter les flexions françaises
    (singulier/pluriel, conjugaisons).
    """
    if not text:
        return []
    clean = _strip_accents(str(text).lower())
    raw_tokens = re.findall(r"[a-z0-9]{2,}", clean)
    tokens: list[str] = []
    for tok in raw_tokens:
        if tok in _FRENCH_STOPWORDS:
            continue
        tokens.append(tok)
        if len(tok) >= 6:
            tokens.append(f"#{tok[:5]}")
    return tokens


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Calcule la similarité cosinus entre deux vecteurs de même dimension en Python pur."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a <= 1e-12 or norm_b <= 1e-12:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


def _compute_lexical_scores(query: str, chunks: list[dict[str, Any]]) -> list[float]:
    """
    Calcule un score de pertinence hybride BM25 / TF-IDF cosinus + couverture IDF
    des termes de la requête, calibré sur [0.0, 1.0].
    """
    q_tokens = _tokenize_lexical(query)
    if not q_tokens or not chunks:
        return [0.0 for _ in chunks]

    doc_tokens_list = [
        _tokenize_lexical(f"{c.get('titre', '')} {c.get('article_ref', '')} {c.get('chunk_text', '')}")
        for c in chunks
    ]

    n_docs = len(chunks)
    df: Counter[str] = Counter()
    for d_toks in doc_tokens_list:
        for tok in set(d_toks):
            df[tok] += 1

    def idf(term: str) -> float:
        return math.log(1.0 + (n_docs + 1.0) / (df.get(term, 0) + 0.5))

    q_counts = Counter(q_tokens)
    q_unique = set(q_tokens)
    q_weights = {t: (1.0 + math.log(cnt)) * idf(t) for t, cnt in q_counts.items()}
    q_norm = math.sqrt(sum(w * w for w in q_weights.values())) or 1.0
    q_idf_sum = sum(idf(t) for t in q_unique) or 1.0

    # Tokens exacts (hors radicaux #...) pour vérifier le chevauchement réel
    q_exact = {t for t in q_unique if not t.startswith("#")}

    scores: list[float] = []
    for d_toks in doc_tokens_list:
        if not d_toks:
            scores.append(0.0)
            continue

        d_unique = set(d_toks)
        shared = q_unique & d_unique
        if not shared:
            scores.append(0.0)
            continue

        d_counts = Counter(d_toks)
        d_weights = {t: (1.0 + math.log(cnt)) * idf(t) for t, cnt in d_counts.items()}
        d_norm = math.sqrt(sum(w * w for w in d_weights.values())) or 1.0

        dot = sum(q_weights[t] * d_weights[t] for t in shared)
        tfidf_cos = dot / (q_norm * d_norm)

        idf_recall = sum(idf(t) for t in shared) / q_idf_sum

        exact_matches = len(q_exact & d_unique)
        bonus = 0.15 if exact_matches >= 2 else (0.08 if exact_matches == 1 and len(q_exact) == 1 else 0.0)

        combined = 0.65 * idf_recall + 0.35 * tfidf_cos + bonus
        scores.append(round(max(0.0, min(1.0, combined)), 4))

    return scores


class PersistentRAGStore:
    """
    Store vectoriel et lexical persistant sur SQLite (`data/bourbon_rag.db`).
    """

    def __init__(
        self,
        db_path: Optional[str | Path] = None,
        embedding_endpoint: Optional[str] = None,
        embedding_model: Optional[str] = None,
        api_key: str = "local-key",
    ):
        if db_path is not None:
            resolved_path = resolve_sqlite_db_path(default_path=db_path) if os.environ.get("VERCEL") else Path(db_path)
            try:
                resolved_path.parent.mkdir(parents=True, exist_ok=True)
                if not os.access(resolved_path.parent, os.W_OK):
                    resolved_path = VERCEL_FALLBACK_DB_PATH
            except OSError:
                resolved_path = VERCEL_FALLBACK_DB_PATH
        else:
            resolved_path = resolve_sqlite_db_path()
        self.db_path = resolved_path

        explicit_endpoint = embedding_endpoint or os.getenv("BOURBON_EMBEDDING_ENDPOINT")
        if explicit_endpoint:
            self.embedding_endpoint = validate_endpoint_url(explicit_endpoint)
        else:
            try:
                self.embedding_endpoint = validate_endpoint_url(DEFAULT_EMBEDDING_ENDPOINT)
            except ValueError:
                # Sur Vercel Serverless sans endpoint distant configuré, le RAG fonctionne en mode lexical pur.
                self.embedding_endpoint = None
        self.embedding_model = embedding_model or os.getenv("BOURBON_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        self.api_key = api_key
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    titre TEXT NOT NULL DEFAULT '',
                    article_ref TEXT NOT NULL DEFAULT '',
                    source_type TEXT NOT NULL DEFAULT 'general',
                    chunk_text TEXT NOT NULL,
                    embedding_json TEXT NOT NULL DEFAULT '[]',
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_doc_id ON rag_chunks(doc_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_source_type ON rag_chunks(source_type)")
            conn.commit()

    def fetch_local_embedding(self, text: str, timeout: float = 2.0) -> list[float]:
        """
        Interroge un serveur d'embeddings local compatible OpenAI (`/v1/embeddings`
        pour LM Studio / Ollama) et retourne le vecteur float, ou `[]` si hors-ligne.
        """
        clean = (text or "").strip()
        if not clean or not self.embedding_endpoint:
            return []
        base = self.embedding_endpoint.rstrip("/")
        url = f"{base}/embeddings" if base.endswith("/v1") else f"{base}/v1/embeddings"
        try:
            validate_endpoint_url(url)
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(
                    url,
                    headers=headers,
                    json={"model": self.embedding_model, "input": clean[:4000]},
                )
                if resp.status_code == 200:
                    payload = resp.json()
                    data = payload.get("data") or []
                    if data and isinstance(data[0], dict) and isinstance(data[0].get("embedding"), list):
                        return [float(x) for x in data[0]["embedding"]]
        except Exception as exc:
            logger.debug(f"Serveur d'embeddings local non disponible ({exc}) -> repli lexical actif.")
        return []

    def ingest_chunk(
        self,
        doc_id: str,
        chunk_text: str,
        titre: str = "",
        article_ref: str = "",
        source_type: str = "general",
        embedding: Optional[list[float]] = None,
        try_remote_embedding: bool = False,
    ) -> str:
        """Insère ou met à jour un chunk sourcé dans SQLite."""
        clean_text = (chunk_text or "").strip()
        if not doc_id or not clean_text:
            raise ValueError("doc_id et chunk_text sont obligatoires.")

        raw_key = f"{doc_id}|{article_ref}|{clean_text}"
        chunk_id = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:24]

        vec = embedding if embedding is not None else (
            self.fetch_local_embedding(clean_text) if try_remote_embedding else []
        )
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO rag_chunks (
                    chunk_id, doc_id, titre, article_ref, source_type, chunk_text, embedding_json, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    titre = excluded.titre,
                    source_type = excluded.source_type,
                    embedding_json = CASE
                        WHEN excluded.embedding_json != '[]' THEN excluded.embedding_json
                        ELSE rag_chunks.embedding_json
                    END,
                    updated_at = excluded.updated_at
                """,
                (
                    chunk_id,
                    str(doc_id).strip(),
                    str(titre or "").strip(),
                    str(article_ref or "").strip(),
                    str(source_type or "general").strip(),
                    clean_text,
                    json.dumps(vec),
                    now_iso,
                ),
            )
            conn.commit()
        return chunk_id

    def ingest_documents(
        self,
        documents: list[dict[str, Any]],
        try_remote_embedding: bool = False,
    ) -> int:
        """
        Ingère une liste de documents ou de chunks dans la base SQLite.
        Accepte :
          - Des chunks directs : `{"doc_id": ..., "titre": ..., "article_ref": ..., "chunk_text": ...}`
          - Des directives structurées : `{"celex_id": ..., "title": ..., "articles": [{"article_id": ..., "content": ...}]}`
        """
        inserted = 0
        for doc in documents or []:
            if not isinstance(doc, dict):
                continue

            doc_id = str(doc.get("doc_id") or doc.get("celex_id") or doc.get("id") or "").strip()
            titre = str(doc.get("titre") or doc.get("title") or "").strip()
            source_type = str(doc.get("source_type") or ("directive_ue" if doc.get("celex_id") else "general")).strip()

            articles = doc.get("articles")
            if isinstance(articles, list) and doc_id:
                for art in articles:
                    if not isinstance(art, dict):
                        continue
                    art_ref = str(art.get("article_ref") or art.get("article_id") or art.get("id") or "Art.").strip()
                    art_title = str(art.get("titre") or art.get("title") or titre).strip()
                    text = str(art.get("chunk_text") or art.get("content") or art.get("text") or "").strip()
                    if text:
                        self.ingest_chunk(
                            doc_id=doc_id,
                            chunk_text=text,
                            titre=art_title,
                            article_ref=art_ref,
                            source_type=source_type,
                            embedding=art.get("embedding"),
                            try_remote_embedding=try_remote_embedding,
                        )
                        inserted += 1
                continue

            chunk_text = str(doc.get("chunk_text") or doc.get("content") or doc.get("text") or "").strip()
            article_ref = str(doc.get("article_ref") or doc.get("article_id") or doc.get("article") or "").strip()
            if doc_id and chunk_text:
                self.ingest_chunk(
                    doc_id=doc_id,
                    chunk_text=chunk_text,
                    titre=titre,
                    article_ref=article_ref,
                    source_type=source_type,
                    embedding=doc.get("embedding"),
                    try_remote_embedding=try_remote_embedding,
                )
                inserted += 1
        return inserted

    def count_chunks(self, source_type: Optional[str] = None) -> int:
        with self._connect() as conn:
            if source_type:
                row = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM rag_chunks WHERE source_type = ?",
                    (source_type,),
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) AS cnt FROM rag_chunks").fetchone()
            return int(row["cnt"]) if row else 0

    def list_sources_summary(self) -> dict[str, Any]:
        with self._connect() as conn:
            total = self.count_chunks()
            rows = conn.execute(
                "SELECT source_type, COUNT(*) AS cnt FROM rag_chunks GROUP BY source_type"
            ).fetchall()
            docs = conn.execute("SELECT COUNT(DISTINCT doc_id) AS dcnt FROM rag_chunks").fetchone()
            return {
                "total_chunks": total,
                "total_documents": int(docs["dcnt"]) if docs else 0,
                "by_source_type": {r["source_type"]: int(r["cnt"]) for r in rows},
                "db_path": str(self.db_path),
            }

    def clear(self) -> int:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM rag_chunks")
            conn.commit()
            return cur.rowcount

    def query_rag(
        self,
        question: str,
        top_k: int = 5,
        min_score: float = 0.45,
        source_type: Optional[str] = None,
        doc_id: Optional[str] = None,
        try_remote_embedding: bool = False,
    ) -> dict[str, Any]:
        """
        Recherche hybride (Cosinus vectoriel + BM25/TF-IDF lexical) dans SQLite.
        Grounding strict : retourne `"Information non disponible dans les sources"`
        si la base est vide ou qu'aucun chunk n'atteint `min_score`.
        """
        clean_q = (question or "").strip()
        if not clean_q:
            return {
                "status": "no_source",
                "answer": STRICT_NO_SOURCE_MESSAGE,
                "message": STRICT_NO_SOURCE_MESSAGE,
                "results": [],
                "sources": [],
            }

        sql = "SELECT chunk_id, doc_id, titre, article_ref, source_type, chunk_text, embedding_json, updated_at FROM rag_chunks WHERE 1=1"
        params: list[Any] = []
        if source_type:
            sql += " AND source_type = ?"
            params.append(source_type)
        if doc_id:
            sql += " AND doc_id = ?"
            params.append(doc_id)

        with self._connect() as conn:
            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]

        if not rows:
            return {
                "status": "no_source",
                "answer": STRICT_NO_SOURCE_MESSAGE,
                "message": STRICT_NO_SOURCE_MESSAGE,
                "results": [],
                "sources": [],
            }

        lex_scores = _compute_lexical_scores(clean_q, rows)
        query_vec = self.fetch_local_embedding(clean_q) if try_remote_embedding else []

        scored_items: list[dict[str, Any]] = []
        for row, lex_score in zip(rows, lex_scores):
            vec_score = 0.0
            if query_vec:
                try:
                    chunk_vec = json.loads(row.get("embedding_json") or "[]")
                    if isinstance(chunk_vec, list) and len(chunk_vec) == len(query_vec):
                        vec_score = cosine_similarity(query_vec, [float(x) for x in chunk_vec])
                except Exception:
                    vec_score = 0.0

            final_score = max(lex_score, vec_score) if query_vec else lex_score
            if final_score >= min_score:
                scored_items.append({
                    "chunk_id": row["chunk_id"],
                    "doc_id": row["doc_id"],
                    "titre": row["titre"],
                    "article_ref": row["article_ref"],
                    "source_type": row["source_type"],
                    "chunk_text": row["chunk_text"],
                    "score": round(float(final_score), 4),
                    "updated_at": row["updated_at"],
                })

        scored_items.sort(key=lambda item: item["score"], reverse=True)
        top_results = scored_items[: max(1, top_k)]

        if not top_results:
            return {
                "status": "no_source",
                "answer": STRICT_NO_SOURCE_MESSAGE,
                "message": STRICT_NO_SOURCE_MESSAGE,
                "results": [],
                "sources": [],
            }

        citations = [
            f"[{r['doc_id']}" + (f" · {r['article_ref']}" if r.get("article_ref") else "") + f"] {r['chunk_text']}"
            for r in top_results
        ]
        answer = "\n".join(citations)

        return {
            "status": "ok",
            "answer": answer,
            "message": f"{len(top_results)} source(s) pertinente(s) trouvée(s).",
            "results": top_results,
            "sources": top_results,
        }

    def seed_default_corpus(self) -> int:
        """
        Pré-remplit le store SQLite avec le socle de directives européennes et de règles
        constitutionnelles / Règlement AN si la base est vide.
        """
        if self.count_chunks() > 0:
            return 0

        baseline_docs = [
            {
                "doc_id": "32014L0024",
                "titre": "Directive 2014/24/UE sur la passation des marchés publics",
                "source_type": "directive_ue",
                "articles": [
                    {
                        "article_ref": "Article 18",
                        "titre": "Principes de la passation de marchés",
                        "chunk_text": "Les pouvoirs adjudicateurs traitent les opérateurs économiques sur un pied d'égalité et sans discrimination et agissent d'une manière transparente et proportionnée.",
                    },
                    {
                        "article_ref": "Article 57",
                        "titre": "Motifs d'exclusion",
                        "chunk_text": "Les pouvoirs adjudicateurs excluent un opérateur économique de la participation à une procédure de passation de marché lorsqu'ils ont établi une condamnation définitive.",
                    },
                ],
            },
            {
                "doc_id": "32019L1937",
                "titre": "Directive (UE) 2019/1937 sur la protection des lanceurs d'alerte",
                "source_type": "directive_ue",
                "articles": [
                    {
                        "article_ref": "Article 9",
                        "titre": "Procédures de signalement interne et de suivi",
                        "chunk_text": "Un accusé de réception du signalement est adressé à l'auteur dans un délai de sept jours et un retour d'information dans un délai raisonnable n'excédant pas trois mois.",
                    },
                    {
                        "article_ref": "Article 19",
                        "titre": "Interdiction de représailles",
                        "chunk_text": "Les États membres prennent les mesures nécessaires pour interdire toute forme de représailles, y compris les menaces et tentatives de représailles envers les auteurs de signalement.",
                    },
                ],
            },
            {
                "doc_id": "32022L2464",
                "titre": "Directive (UE) 2022/2464 (CSRD) sur la publication d'informations en matière de durabilité",
                "source_type": "directive_ue",
                "articles": [
                    {
                        "article_ref": "Article 19 bis",
                        "titre": "Information en matière de durabilité",
                        "chunk_text": "Les grandes entreprises incluent dans le rapport de gestion des informations permettant de comprendre les incidences de l'entreprise sur les questions de durabilité.",
                    },
                ],
            },
            {
                "doc_id": "CONST-1958",
                "titre": "Constitution du 4 octobre 1958 — Recevabilité parlementaire",
                "source_type": "regle_irrecevabilite",
                "articles": [
                    {
                        "article_ref": "Article 40",
                        "titre": "Irrecevabilité financière",
                        "chunk_text": "Les propositions et amendements formulés par les membres du Parlement ne sont pas recevables lorsque leur adoption aurait pour conséquence soit une diminution des ressources publiques, soit la création ou l'aggravation d'une charge publique.",
                    },
                    {
                        "article_ref": "Article 45",
                        "titre": "Lien avec le texte et cavaliers législatifs",
                        "chunk_text": "Tout projet ou proposition de loi est examiné successivement dans les deux assemblées. Sans préjudice du premier alinéa de l'article 44, tout amendement est recevable en première lecture dès lors qu'il présente un lien, même indirect, avec le texte déposé ou transmis.",
                    },
                ],
            },
            {
                "doc_id": "RAN-2026",
                "titre": "Règlement de l'Assemblée nationale",
                "source_type": "regle_irrecevabilite",
                "articles": [
                    {
                        "article_ref": "Article 98",
                        "titre": "Dépôt, recevabilité et ordre d'appel des amendements",
                        "chunk_text": "Les amendements sont mis en discussion en commençant par ceux qui demandent la suppression de l'article, puis par ceux qui s'écartent le plus du texte proposé et dans l'ordre des alinéas.",
                    },
                ],
            },
        ]
        return self.ingest_documents(baseline_docs, try_remote_embedding=False)


_DEFAULT_STORE: Optional[PersistentRAGStore] = None


def get_default_rag_store(db_path: Optional[str | Path] = None) -> PersistentRAGStore:
    """Retourne l'instance singleton du store SQLite (ou une instance dédiée si db_path est fourni)."""
    global _DEFAULT_STORE
    if db_path is not None:
        return PersistentRAGStore(db_path=db_path)
    resolved = resolve_sqlite_db_path()
    if _DEFAULT_STORE is None or _DEFAULT_STORE.db_path != resolved:
        _DEFAULT_STORE = PersistentRAGStore(db_path=resolved)
        _DEFAULT_STORE.seed_default_corpus()
    return _DEFAULT_STORE


def query_rag(
    question: str,
    top_k: int = 5,
    min_score: float = 0.45,
    db_path: Optional[str | Path] = None,
    source_type: Optional[str] = None,
    doc_id: Optional[str] = None,
    store: Optional[PersistentRAGStore] = None,
) -> dict[str, Any]:
    """
    Fonction principale de recherche RAG sourcée avec seuil de confiance strict (`min_score=0.45`).
    Retourne explicitement `"Information non disponible dans les sources"` si aucun chunk ne dépasse le seuil.
    """
    target_store = store or get_default_rag_store(db_path=db_path)
    return target_store.query_rag(
        question=question,
        top_k=top_k,
        min_score=min_score,
        source_type=source_type,
        doc_id=doc_id,
    )
