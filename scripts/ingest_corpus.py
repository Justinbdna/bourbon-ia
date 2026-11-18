#!/usr/bin/env python3
"""
scripts/ingest_corpus.py — CLI d'ingestion massive pour Bourbon.IA
===================================================================
Permet de charger hors-ligne dans `bourbon_rag.db` (ou `BOURBON_DB_PATH`) :
  - les règles d'irrecevabilité (--rules)
  - les déclarations Open Data HATVP (--hatvp)
  - l'historique des scrutins & interventions (--history)
  - les documents de référence .md, .txt, .json (--docs)
  - et d'inspecter le volume indexé dans les 4 tables (--status)

Exemples d'usage :
    python3 scripts/ingest_corpus.py --status
    python3 scripts/ingest_corpus.py --rules data/regles_384.json
    python3 scripts/ingest_corpus.py --hatvp data/hatvp_export.csv
    python3 scripts/ingest_corpus.py --history data/scrutins_17e.json
    python3 scripts/ingest_corpus.py --docs data/corpus_juridique/
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

# Assure l'import de `api.*` même si exécuté depuis un autre répertoire
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from api.services.chrono_debunker import ChronoDebunkerStore  # noqa: E402
from api.services.hatvp_graph import HATVPGraphStore  # noqa: E402
from api.services.rag_store import PersistentRAGStore, resolve_sqlite_db_path  # noqa: E402
from api.services.rules_engine import LegislativeRulesEngine  # noqa: E402


def _read_csv_rows(content: str) -> list[dict[str, Any]]:
    lines = content.splitlines()
    if not lines:
        return []
    delimiter = ";" if lines[0].count(";") > lines[0].count(",") else ","
    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
    return [dict(row) for row in reader]


def ingest_rules_file(file_path: Path, engine: LegislativeRulesEngine) -> int:
    if not file_path.is_file():
        raise FileNotFoundError(f"Fichier de règles introuvable : {file_path}")
    content = file_path.read_text(encoding="utf-8")
    ext = file_path.suffix.lower()

    if ext == ".json":
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            payload = parsed.get("rules") or parsed.get("regles") or [parsed]
        else:
            payload = parsed
        return engine.ingest_rules(payload)

    if ext == ".csv":
        rows = _read_csv_rows(content)
        normalized = []
        for row in rows:
            raw_kws = row.get("mots_cles_declencheurs") or row.get("mots_cles") or ""
            kws = [k.strip() for k in re.split(r"[;|,]", raw_kws) if k.strip()]
            normalized.append({
                "rule_id": row.get("rule_id") or row.get("id") or "",
                "code_article": row.get("code_article") or row.get("article") or "",
                "categorie": row.get("categorie") or "",
                "titre": row.get("titre") or row.get("title") or "",
                "description": row.get("description") or row.get("texte") or "",
                "mots_cles_declencheurs": kws,
                "severite": row.get("severite") or "HAUTE",
            })
        return engine.ingest_rules(normalized)

    return engine.ingest_rules(content)


def ingest_hatvp_file(file_path: Path, store: HATVPGraphStore) -> int:
    if not file_path.is_file():
        raise FileNotFoundError(f"Fichier HATVP introuvable : {file_path}")
    content = file_path.read_text(encoding="utf-8")
    ext = file_path.suffix.lower()

    if ext == ".json":
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            payload = (
                parsed.get("declarations")
                or parsed.get("representants")
                or parsed.get("publications")
                or [parsed]
            )
        else:
            payload = parsed
        return store.ingest_declarations(payload)

    if ext == ".csv":
        return store.ingest_declarations(_read_csv_rows(content))

    raise ValueError(f"Format HATVP non supporté ({ext}) : utiliser .json ou .csv.")


def ingest_history_file(file_path: Path, store: ChronoDebunkerStore) -> int:
    if not file_path.is_file():
        raise FileNotFoundError(f"Fichier d'historique introuvable : {file_path}")
    content = file_path.read_text(encoding="utf-8")
    ext = file_path.suffix.lower()

    if ext == ".json":
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            payload = (
                parsed.get("entries")
                or parsed.get("scrutins")
                or parsed.get("historique")
                or [parsed]
            )
        else:
            payload = parsed
        return store.ingest_history(payload)

    if ext == ".csv":
        return store.ingest_history(_read_csv_rows(content))

    raise ValueError(f"Format historique non supporté ({ext}) : utiliser .json ou .csv.")


def _chunk_text_by_sections(
    text: str,
    default_title: str,
    max_chars: int = 1200,
) -> list[tuple[str, str]]:
    """
    Découpe un texte Markdown/TXT en couples `(article_ref, chunk_text)` en
    respectant les titres `#` / `##` / `###` et les limites de paragraphes.
    """
    chunks: list[tuple[str, str]] = []
    current_heading = default_title
    buffer: list[str] = []
    buffer_len = 0

    def _flush() -> None:
        nonlocal buffer, buffer_len
        joined = "\n\n".join(buffer).strip()
        if joined:
            chunks.append((current_heading, joined))
        buffer = []
        buffer_len = 0

    for block in re.split(r"\n\s*\n", text.strip()):
        clean_block = block.strip()
        if not clean_block:
            continue
        heading_match = re.match(r"^#{1,4}\s+(.+)$", clean_block.splitlines()[0].strip())
        if heading_match:
            _flush()
            current_heading = heading_match.group(1).strip()
            rest = "\n".join(clean_block.splitlines()[1:]).strip()
            if not rest:
                continue
            clean_block = rest

        if len(clean_block) > max_chars:
            _flush()
            for start in range(0, len(clean_block), max_chars):
                sub = clean_block[start : start + max_chars].strip()
                if sub:
                    chunks.append((current_heading, sub))
            continue

        if buffer_len + len(clean_block) + 2 > max_chars and buffer:
            _flush()

        buffer.append(clean_block)
        buffer_len += len(clean_block) + 2

    _flush()
    return chunks


def ingest_docs_path(
    target: Path,
    rag_store: PersistentRAGStore,
    try_remote_embedding: bool = False,
) -> int:
    if not target.exists():
        raise FileNotFoundError(f"Chemin documentaire introuvable : {target}")

    allowed_exts = {".md", ".txt", ".json"}
    files = (
        [target]
        if target.is_file()
        else sorted(p for p in target.rglob("*") if p.is_file() and p.suffix.lower() in allowed_exts)
    )

    inserted = 0
    for fpath in files:
        ext = fpath.suffix.lower()
        if ext not in allowed_exts:
            continue
        raw = fpath.read_text(encoding="utf-8")
        doc_id = fpath.stem

        if ext == ".json":
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                inserted += rag_store.ingest_documents(parsed, try_remote_embedding=try_remote_embedding)
            elif isinstance(parsed, dict):
                if isinstance(parsed.get("documents"), list):
                    inserted += rag_store.ingest_documents(parsed["documents"], try_remote_embedding=try_remote_embedding)
                elif isinstance(parsed.get("chunks"), list):
                    inserted += rag_store.ingest_documents(parsed["chunks"], try_remote_embedding=try_remote_embedding)
                elif isinstance(parsed.get("articles"), dict):
                    titre = str(parsed.get("titre") or parsed.get("title") or doc_id)
                    doc_key = str(parsed.get("doc_id") or parsed.get("uid") or doc_id)
                    docs_payload = [
                        {
                            "doc_id": doc_key,
                            "titre": titre,
                            "article_ref": str(art_ref),
                            "source_type": "document_reference",
                            "chunk_text": str(art_text),
                        }
                        for art_ref, art_text in parsed["articles"].items()
                        if str(art_text).strip()
                    ]
                    inserted += rag_store.ingest_documents(docs_payload, try_remote_embedding=try_remote_embedding)
                else:
                    if not parsed.get("doc_id"):
                        parsed["doc_id"] = doc_id
                    inserted += rag_store.ingest_documents([parsed], try_remote_embedding=try_remote_embedding)
            continue

        sections = _chunk_text_by_sections(raw, default_title=doc_id)
        for idx, (art_ref, chunk_text) in enumerate(sections, start=1):
            rag_store.ingest_chunk(
                doc_id=doc_id,
                titre=doc_id.replace("_", " "),
                article_ref=art_ref or f"Section {idx}",
                source_type="document_reference",
                chunk_text=chunk_text,
                try_remote_embedding=try_remote_embedding,
            )
            inserted += 1

    return inserted


def get_database_status(db_path: Optional[Path] = None) -> dict[str, Any]:
    resolved = db_path if db_path is not None else resolve_sqlite_db_path()
    rag_store = PersistentRAGStore(db_path=resolved)
    rules_engine = LegislativeRulesEngine(db_path=resolved)
    hatvp_store = HATVPGraphStore(db_path=resolved)
    debunker_store = ChronoDebunkerStore(db_path=resolved)

    return {
        "db_path": str(resolved),
        "tables": {
            "rag_chunks": rag_store.count_chunks(),
            "legislative_rules": rules_engine.count_rules(),
            "hatvp_declarations": hatvp_store.count_declarations(),
            "parliamentary_history": debunker_store.count_entries(),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CLI d'ingestion massive et d'inspection pour Bourbon.IA (bourbon_rag.db)."
    )
    parser.add_argument("--rules", type=Path, help="Fichier de règles d'irrecevabilité (.json, .csv, .md)")
    parser.add_argument("--hatvp", type=Path, help="Fichier Open Data HATVP (.json, .csv)")
    parser.add_argument("--history", type=Path, help="Fichier historique des scrutins/interventions (.json, .csv)")
    parser.add_argument("--docs", type=Path, help="Dossier ou fichier documentaire (.md, .txt, .json)")
    parser.add_argument("--status", action="store_true", help="Affiche le nombre d'entrées des 4 tables SQLite")
    parser.add_argument("--db-path", type=Path, default=None, help="Chemin explicite vers la base SQLite")
    parser.add_argument(
        "--try-embeddings",
        action="store_true",
        help="Tente le calcul d'embeddings via le serveur local (/v1/embeddings) lors de --docs",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not any([args.rules, args.hatvp, args.history, args.docs, args.status]):
        parser.print_help()
        return 0

    resolved_db = args.db_path if args.db_path is not None else resolve_sqlite_db_path()

    if args.rules:
        engine = LegislativeRulesEngine(db_path=resolved_db)
        n = ingest_rules_file(args.rules, engine)
        print(f"✅ Règles ingérées : {n} (total legislative_rules = {engine.count_rules()})")

    if args.hatvp:
        hatvp = HATVPGraphStore(db_path=resolved_db)
        n = ingest_hatvp_file(args.hatvp, hatvp)
        print(f"✅ Déclarations HATVP ingérées : {n} (total hatvp_declarations = {hatvp.count_declarations()})")

    if args.history:
        debunker = ChronoDebunkerStore(db_path=resolved_db)
        n = ingest_history_file(args.history, debunker)
        print(f"✅ Historique parlementaire ingéré : {n} (total parliamentary_history = {debunker.count_entries()})")

    if args.docs:
        rag = PersistentRAGStore(db_path=resolved_db)
        n = ingest_docs_path(args.docs, rag, try_remote_embedding=args.try_embeddings)
        print(f"✅ Chunks documentaires ingérés : {n} (total rag_chunks = {rag.count_chunks()})")

    if args.status:
        status = get_database_status(db_path=resolved_db)
        tables = status["tables"]
        print(f"📊 État de la base SQLite : {status['db_path']}")
        print(f"  - rag_chunks            : {tables['rag_chunks']} entrée(s)")
        print(f"  - legislative_rules     : {tables['legislative_rules']} entrée(s)")
        print(f"  - hatvp_declarations    : {tables['hatvp_declarations']} entrée(s)")
        print(f"  - parliamentary_history : {tables['parliamentary_history']} entrée(s)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
