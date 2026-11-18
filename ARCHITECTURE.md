# 🏛️ BOURBON.IA — Architecture Technique (v2.0)

Ce document décrit l'architecture de production de **Bourbon.IA**, conçue pour fonctionner en environnement **Air-Gapped** (`BOURBON_TEXTES_DISTANTS=0` par défaut) avec inférence locale (Ollama / LM Studio) et passage à l'échelle sur serveur GPU.

---

## 1️⃣ Vue d'Ensemble du Pipeline

```text
  [ React / Vite UI ]  <── HTTP / GZip ──>  [ FastAPI (api/index.py) ]
         │                                           │
         │                                  ┌────────┴────────┐
         │                                  ▼                 ▼
         │                       Moteur Déterministe    Services SQLite (data/bourbon_rag.db)
         │                       (< 150ms, 0 LLM)       • RAG Store (rag_store.py)
         │                                  │           • 384 Règles (rules_engine.py)
         │                                  │           • Graphe HATVP (hatvp_graph.py)
         │                                  │           • Debunker (chrono_debunker.py)
         │                                  ▼
         │                       File Batch GPU (batch_job_queue.py) & LLM Local
         │
  [ Client MCP Local ] <── stdio JSON-RPC ──> [ mcp_server.py ]
```

---

## 2️⃣ Composants Backend (`api/`)

| Module | Rôle |
| :--- | :--- |
| `api/index.py` | Point d'entrée FastAPI : normalisation AN, routes V2 (`/api/v2/mecanique`, `/api/v2/classer-regles`, `/api/v2/analyser-llm`, `/api/v2/resumer`, `/api/v2/surtransposition`, `/api/v2/rag/*`, `/api/v2/rules/*`, `/api/v2/hatvp/*`, `/api/v2/debunker/*`, `/api/v2/jobs/*`, `/api/v2/export-prejaune`). |
| `api/services/deterministic_classifier.py` | Classement légistique ultra-rapide (`Identique`, `Discussion commune`, `Isolé`), détection des plages d'alinéas, des amendements tombants (`tombe_si_adoption_de`) et calcul d'empreinte. |
| `api/deterministic_engine.py` | Pipeline déterministe enrichi, résolution des sous-amendements, qualification des irrecevabilités et tri parlementaire. |
| `api/legal_chapeau_parser.py` & `api/legal_typography.py` | Analyse syntaxique des chapeaux AN/Sénat, priorité au dérouleur, audit Art. 40, détection des dispositions non normatives (Art. 6 DDHC) et normalisation typographique DILA. |
| `api/services/rag_store.py` | Store vectoriel & lexical persistant SQLite (`data/bourbon_rag.db`), embeddings locaux (`/v1/embeddings`), repli BM25/TF-IDF et grounding strict (`"Information non disponible dans les sources"`). |
| `api/services/rules_engine.py` | Catalogue SQLite extensible des 384 règles d'irrecevabilité : Art. 40 C., Art. 45 C. (proximité cavalier législatif) et Art. 98 RAN (priorité d'appel 1 à 5). |
| `api/services/hatvp_graph.py` | Base locale des déclarations HATVP et scoring de proximité thématique sourcé. |
| `api/services/chrono_debunker.py` | Historique daté des scrutins et interventions par `acteur_ref` / groupe avec détection de contradictions et repli `no_history`. |
| `api/services/batch_job_queue.py` | File de jobs asynchrone (`BatchJobManager`) levant la limite jusqu'à `BOURBON_MAX_AMENDEMENTS` (25 000). |
| `api/llm_semantic_engine.py` | Inférence LLM locale/custom avec protection anti-SSRF (résolution DNS), masquage des clés API et validation Pydantic Chain-of-Thought. |
| `mcp_server.py` | Serveur Model Context Protocol exposant 7 outils métier locaux aux clients MCP. |

---

## 3️⃣ Composants Frontend (`src/`)

- **Tableau & Recherche (`src/components/AmendmentTable.jsx`, `AmendmentSearchBar.jsx`)** : filtres multicritères (Article, Groupe politique, Thème, Auteur), badges `⚠️ Tombe si adoption de ...`, `✍️ Arbitré manuellement`, pagination et réordonnancement.
- **Volet Détail & Comparateur (`src/components/AmendmentDetail.jsx`)** : comparateur mot-à-mot **Loi initiale vs Amendement** (`computeWordDiff`), sélecteur rapide d'arbitrage manuel, résumé IA à la demande et panneau de conformité européenne.
- **Exports & Sécurité (`src/utils/exportRtf.js`, `exportEloi.js`, `crypto.js`)** : génération RTF Préjaune respectant l'arbitrage manuel, export Éloi JSON, chiffrement AES-GCM par blocs dans `sessionStorage`/`localStorage`.

---

## 4️⃣ Déploiement & Tests

- **Docker Air-Gapped** : `Dockerfile` multi-stage (build Vite + runtime Python 3.12) et `docker-compose.yml` (FastAPI + Ollama avec volume persistant `/app/data`).
- **Tests** : `python3 -m pytest -W error::DeprecationWarning` (165 tests) et `npm test -- --run` (44 tests).
