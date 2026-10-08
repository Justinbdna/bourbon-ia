---
trigger: always_on
description: "Architectural rules for EU compliance and surtransposition analysis in Bourbon.IA"
---

# Bourbon.IA - EU Compliance & Surtransposition Module Constraints

## Architectural Principles
1. **Strict Data Privacy & Air-Gapped Execution:**
   - Confidential draft amendments MUST NEVER leave the local environment or be sent to external APIs.
   - External APIs (EUR-Lex / Légifrance / AN Open Data) are for READ-ONLY baseline data ingestion.

2. **Ingest-Then-Process Pattern:**
   - Ingest public regulatory references via API -> Store in local vector DB (e.g., Qdrant / PGVector / ChromaDB).
   - Perform local RAG and LLM inference entirely on-device or on local infrastructure.

3. **Tech Stack Requirements:**
   - Backend: Python (FastAPI) or Node.js/TypeScript.
   - Local Embeddings: HuggingFace / sentence-transformers (`multilingual-e5-small` or `bge-m3`).
   - Vector Store: Local vector instance (Qdrant client or local SQLite + vec extension).
