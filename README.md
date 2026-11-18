# 🇫🇷 Bourbon.IA — Assistant Législatif Souverain (v2.0)

**Bourbon.IA** est un assistant législatif 100 % local et **Air-Gapped** conçu pour les équipes parlementaires de l'Assemblée nationale. Il trie, classe, contrôle la recevabilité et source des liasses massives d'amendements sans aucune fuite de données vers des API Cloud externes.

---

## 🎯 Fonctionnalités Clés (v2.0)

1. **Moteur Déterministe Légistique (`< 150 ms` sur 341 amendements)** :
   - Détection exacte des **Identiques (`[Id.]`)**, **Doublons**, **Discussions communes (`[Dc.]`)** et **Isolés** sans appel LLM.
   - **Amendements tombants** (`tombe_si_adoption_de`) : identification automatique des amendements devenant sans objet en cas d'adoption d'une suppression d'article.
   - **Audit constitutionnel & Règlement AN** : détection de gage financier (**Art. 40 C.**), risque de cavalier législatif (**Art. 45 C.**) et ordre d'appel strict en séance (**Art. 98 RAN**).
   - **Human-in-the-Loop** : requalification manuelle en 1 clic (`arbitrage_manuel`) préservée lors des passes IA et dans l'export **Préjaune RTF** / **Éloi JSON**.

2. **Architecture Souveraine Air-Gap** :
   - `BOURBON_TEXTES_DISTANTS=0` par défaut (aucun appel réseau sortant non sollicité).
   - Zéro dépendance Cloud / CDN externe côté interface (polices locales, provider IA local par défaut).
   - Protection anti-SSRF avec résolution DNS et chiffrement AES-GCM côté navigateur.

3. **Intelligence Juridique & Store RAG Persistant (`data/bourbon_rag.db`)** :
   - **Store RAG SQLite persistant** ([api/services/rag_store.py](file:///Users/jujutravail/bourbon-ia/api/services/rag_store.py)) : embeddings locaux (`/v1/embeddings` LM Studio / Ollama `bge-m3`) avec repli lexical BM25/TF-IDF et grounding strict (`"Information non disponible dans les sources"` sous le seuil).
   - **Moteur des Règles d'Irrecevabilité (384 règles)** ([api/services/rules_engine.py](file:///Users/jujutravail/bourbon-ia/api/services/rules_engine.py)) : catalogue extensible JSON/CSV/MD et évaluation Art. 40 / Art. 45 / Art. 98.
   - **Graphe d'influence HATVP** ([api/services/hatvp_graph.py](file:///Users/jujutravail/bourbon-ia/api/services/hatvp_graph.py)) : croisement hors-ligne avec les déclarations Open Data HATVP.
   - **Debunker Chronologique** ([api/services/chrono_debunker.py](file:///Users/jujutravail/bourbon-ia/api/services/chrono_debunker.py)) : vérification datée des scrutins et interventions parlementaires.
   - **File de Jobs Batch GPU** ([api/services/batch_job_queue.py](file:///Users/jujutravail/bourbon-ia/api/services/batch_job_queue.py)) : traitement asynchrone jusqu'à `BOURBON_MAX_AMENDEMENTS` (25 000 par défaut) via `/api/v2/jobs/submit` et `/api/v2/jobs/{job_id}`.

4. **Serveur MCP Python (`mcp_server.py`)** :
   - Expose les outils Bourbon.IA en local (`classer_liasse_mecanique`, `inspecter_amendement`, `rechercher_sources_rag`, `generer_prejaune_rtf`, `evaluer_regles_irrecevabilite`, `verifier_influence_hatvp`, `debunker_historique_acteur`).

---

## ⚙️ Installation & Lancement Rapide

### Option 1 : Exécution locale (Python + Node.js)

```bash
# Backend FastAPI (port 8000)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.index:app --reload --port 8000

# Frontend React / Vite (port 5173)
npm install
npm run dev
```

### Option 2 : Déploiement Conteneurisé Souverain (Docker + Ollama)

```bash
docker compose up --build
```

---

## 🧪 Tests & Qualité

```bash
# Tests Backend (162 tests Pytest)
python3 -m pytest -W error::DeprecationWarning

# Tests Frontend (43 tests Vitest), Linter & Build
npm test -- --run
npm run lint
npm run build
```
