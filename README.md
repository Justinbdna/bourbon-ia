# 🇫🇷 Bourbon.IA (v2.0) — Plateforme Légistique Souveraine & Intelligence Parlementaire

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![MCP](https://img.shields.io/badge/MCP-7%20Outils-111827)](./mcp_server.py)
[![Docker Air-Gap](https://img.shields.io/badge/Docker-Air--Gap%20Sovereign-2496ED?logo=docker&logoColor=white)](./Dockerfile)
[![Pytest](https://img.shields.io/badge/Pytest-165%20passed-22C55E)](./tests)
[![Vitest](https://img.shields.io/badge/Vitest-44%20passed-22C55E)](./src/__tests__)

**Bourbon.IA** est une plateforme légistique **100 % locale et souveraine (Air-Gapped)** conçue pour les équipes parlementaires et les administrateurs de séance de l'Assemblée nationale. Elle classe les liasses massives d'amendements en moins de 200 ms sans appel LLM, contrôle la recevabilité constitutionnelle et réglementaire, compare mot-à-mot les textes et source chaque réponse juridique sur base SQLite locale — sans aucune fuite de données avant la séance publique.

---

## 🏛️ Genèse : Du Défi Hackathon Assemblée nationale à Bourbon.IA v2.0

### Le défi d'origine (*Hackathon 2026 de l'Assemblée nationale*)
Bourbon.IA est né lors du **Hackathon 2026 de l'Assemblée nationale** (*« Le parcours de la loi : vers une IA de confiance »*, Table S6 à l'Hôtel de Lassay), sous l'intitulé officiel :

> **« Bourbon.IA : L'Assistant Législatif 100 % Local »**  
> Fiche officielle du défi : [hackathon2026.assemblee-nationale.fr/defis/de85f219-55ec-4ec4-94e0-ea61a4794dda](https://hackathon2026.assemblee-nationale.fr/defis/de85f219-55ec-4ec4-94e0-ea61a4794dda)

**Le constat terrain — « L'enfer des 48 heures » :**  
En 2023, la réforme des retraites a généré plus de **20 400 amendements** déposés en situation d'obstruction parlementaire. Face à cet afflux, un effectif restreint d'administrateurs transpartisans dispose de **moins de 48 heures** pour trier, dédoublonner, ordonner et classer l'ensemble des amendements avant d'alimenter le logiciel officiel de l'Assemblée (*Éloi*).

**Le verrou déontologique :**  
Pendant cette fenêtre critique de 48 heures, les amendements ne sont **pas encore rendus publics**. Par stricte exigence de confidentialité et de séparation des pouvoirs, les administrateurs **ne peuvent envoyer aucun texte vers des IA Cloud externes** ni même vers des API distantes. Les assistants tout-IA classiques sont donc inutilisables précisément là où la charge est maximale.

### L'évolution vers la plateforme Bourbon.IA v2.0
Conçu initialement comme un prototype monolithique de démonstration pendant le Hackathon, Bourbon.IA a été refondu en une **plateforme légistique souveraine complète (v2.0)** :

- **Abandon du tri tout-LLM** au profit d'un **moteur déterministe Python pur** conforme à la doctrine de classement de l'Assemblée nationale, validé à **100 %** sur le jeu témoin JOP 2030 ([reports/temoin_classification_golden.json](reports/temoin_classification_golden.json)).
- **Analyse syntaxique des chapeaux AN/Sénat & typographie DILA** ([api/legal_chapeau_parser.py](api/legal_chapeau_parser.py), [api/legal_typography.py](api/legal_typography.py)) : calcul de priorité au dérouleur, détection des dispositions non normatives (Art. 6 DDHC) et audit financier (Art. 40).
- **Contrôle Approfondi intégré** : catalogue extensible des **384 règles d'irrecevabilité** (Art. 40, Art. 45, Art. 98), graphe d'influence **HATVP** hors-ligne et **debunker chronologique** des scrutins et interventions.
- **Persistance RAG souveraine (`data/bourbon_rag.db`)** : Vector Store SQLite avec embeddings locaux (`/v1/embeddings`), repli lexical BM25 / TF-IDF et repli automatique `/tmp/bourbon_rag.db` en environnement Serverless Vercel.
- **Passerelle MCP & passage à l'échelle GPU** : serveur MCP Python exposant **7 outils** ([mcp_server.py](mcp_server.py)), file de jobs batch jusqu'à **25 000 amendements** (`/api/v2/jobs/*`) et conteneurisation Docker Air-Gap ([Dockerfile](Dockerfile), [docker-compose.yml](docker-compose.yml)).

---

## ⚡ Pourquoi une Architecture Hybride ? (Benchmarks & Souveraineté)

| Critère | Approche Tout-LLM Cloud | Bourbon.IA v2.0 (Hybride Déterministe + IA Locale) |
| :--- | :--- | :--- |
| **Temps de classement (341 amendements)** | Plusieurs dizaines de secondes à plusieurs minutes | **~147 ms** (mesuré `< 165 ms`, seuil CI `< 300 ms`) |
| **Conformité Règlement AN (Art. 98, `[Id.]`, `[Dc.]`)** | Probabiliste, non reproductible | **100 % déterministe** et auditable (120 `[Id.]`, 122 `[Dc.]`, 99 Isolés sur JOP 2030) |
| **Confidentialité avant séance publique** | Fuite potentielle vers serveurs tiers | **Air-Gap strict (`BOURBON_TEXTES_DISTANTS=0`)**, exécution `localhost` / Docker isolé |
| **Usage de l'IA (Mistral / Qwen)** | Systématique sur toute la liasse | **À la demande uniquement** (résumés 3 points, cas ambigus, surtransposition UE) |
| **Hallucinations sur les sources** | Risque d'invention de références | **Grounding strict** : `"Information non disponible dans les sources"` sous le seuil |
| **Contrôle humain** | Boîte noire | **Human-in-the-Loop** : arbitrage manuel en 1 clic prioritaire sur l'IA et les exports |

---

## 🚀 Fonctionnalités Clés de la v2.0

### 1. Moteur Légistique Déterministe (`< 150 ms`)
- **Classement instantané (`POST /api/v2/classer-regles`)** : détection O(N) par empreinte normalisée + distance de Levenshtein (`> 0,98`) des **Identiques (`[Id.]`)**, **Doublons**, **Discussions communes (`[Dc.]`)** (règles A à E, chevauchement de plages d'alinéas) et **Isolés**.
- **Amendements tombants (`tombe_si_adoption_de`)** : liaison automatique des amendements devenant sans objet en cas d'adoption d'une suppression totale d'article, avec badge d'alerte visuel et report RTF.
- **Ordre d'appel en séance (Art. 98 RAN)** : calcul strict des priorités `1` (Suppression d'article) à `5` (Insertion / Adjonction) et ordonnancement du dérouleur.
- **Exports parlementaires natifs** : génération du **Préjaune RTF** officiel (`╓ ║ ╙`, mentions `[Id.]` / `[Dc.]`) côté backend (`/api/v2/export-prejaune`) et frontend ([src/utils/exportRtf.js](src/utils/exportRtf.js)), plus export **Éloi JSON** ([src/utils/exportEloi.js](src/utils/exportEloi.js)).

### 2. Contrôle Approfondi en 1 Clic (`AmendmentDetail`)
Depuis la fiche détaillée d'un amendement, le bouton **« Lancer l'audit approfondi »** croise en parallèle trois moteurs locaux SQLite :
- **Moteur des 384 règles d'irrecevabilité** ([api/services/rules_engine.py](api/services/rules_engine.py)) : audit financier **Article 40 C.** (charges non gagées vs gages Tabac/Alcool/DGF/Sécu), détection de **cavalier législatif Article 45 C.** (score de proximité cosinus/lexicale avec le texte global), priorité **Art. 98 RAN** et alerte de non-normativité **Art. 6 DDHC**.
- **Graphe d'influence HATVP** ([api/services/hatvp_graph.py](api/services/hatvp_graph.py)) : croisement hors-ligne avec les déclarations Open Data de représentants d'intérêts et scoring de proximité thématique sourcé.
- **Debunker chronologique des scrutins** ([api/services/chrono_debunker.py](api/services/chrono_debunker.py)) : vérification datée des votes et interventions parlementaires antérieurs de l'auteur ou du groupe, avec repli explicite sur `"Information non disponible dans les sources"` si aucun historique n'existe.

### 3. Vector Store SQLite Persistant & Grounding Strict
- **Store hybride (`data/bourbon_rag.db`)** ([api/services/rag_store.py](api/services/rag_store.py)) : embeddings locaux via `/v1/embeddings` (Ollama `bge-m3` ou LM Studio `nomic-embed`) avec repli lexical hybride **BM25 / TF-IDF** entièrement hors-ligne.
- **Repli Serverless automatique** : bascule automatiquement sur `/tmp/bourbon_rag.db` lorsque `VERCEL=1` ou lorsque le système de fichiers applicatif est en lecture seule.
- **Zéro hallucination** : sous le seuil de confiance (`min_score = 0.45`), l'API et le serveur MCP retournent strictement `"Information non disponible dans les sources"`.

### 4. Interface Légistique Complète (`max-w-[1440px]`)
- **Tableau pleine largeur responsive (`max-w-[1440px]`)** : tuiles de bilan cliquables, tri parlementaire/chronologique, pagination, badge d'impact et suppression groupée des doublons.
- **Filtrage multicritères instantané** ([src/components/amendment/AmendmentSearchBar.jsx](src/components/amendment/AmendmentSearchBar.jsx)) : filtres combinables par **Article**, **Groupe politique**, **Thème de commission** et **Auteur**.
- **Comparateur visuel mot-à-mot** (`computeWordDiff` dans [src/components/AmendmentDetail.jsx](src/components/AmendmentDetail.jsx)) : différentiel **Loi initiale vs Amendement** (suppressions barrées en rouge, ajouts en vert) et comparaison directe entre amendements concurrents.
- **Arbitrage manuel (*Human-in-the-Loop*)** : requalification en 1 clic (`Isolé`, `Discussion commune`, `Identique`) et choix d'amendement cible, marqués `✍️ Arbitré manuellement` et préservés dans les exports RTF/Éloi.

### 5. Serveur MCP, File Batch GPU & Docker Air-Gap
- **Serveur MCP Python (`mcp_server.py`)** : expose **7 outils** (`classer_liasse_mecanique`, `inspecter_amendement`, `rechercher_sources_rag`, `generer_prejaune_rtf`, `evaluer_regles_irrecevabilite`, `verifier_influence_hatvp`, `debunker_historique_acteur`) sur stdio JSON-RPC / FastMCP.
- **File de jobs batch GPU** ([api/services/batch_job_queue.py](api/services/batch_job_queue.py)) : soumission asynchrone jusqu'à `BOURBON_MAX_AMENDEMENTS` (**25 000 amendements** par défaut) via `POST /api/v2/jobs/submit` et suivi via `GET /api/v2/jobs/{job_id}`.
- **Conteneurisation souveraine** : `Dockerfile` multi-stage (build Vite + runtime Python 3.12) et `docker-compose.yml` couplant le serveur Bourbon.IA et un conteneur `ollama` avec volume persistant `/app/data`.

---

## 🗂️ Architecture du Projet

```text
bourbon-ia/
├── api/                                  # Backend FastAPI & moteurs légistiques
│   ├── index.py                          # Point d'entrée FastAPI & routes /api/v2/*
│   ├── schemas.py                        # Modèles Pydantic (EnrichedAmendment, plafonds)
│   ├── deterministic_engine.py           # Moteur déterministe & qualification Art. 40/45/98
│   ├── legal_chapeau_parser.py           # Parseur syntaxique AN/Sénat, dérouleur & Art. 40
│   ├── legal_typography.py               # Normalisation typographique DILA
│   ├── export_rtf.py                     # Générateur Préjaune RTF natif (crochets ╓ ║ ╙)
│   ├── llm_semantic_engine.py            # Inférence LLM locale, anti-SSRF & masquage secrets
│   ├── cache_manager.py                  # Cache RAM TTL pour résumés/classifications IA
│   ├── transport.py                      # Décompression gzip bornée & Private Network Access
│   ├── tricoteuses_client.py             # Normalisation des schémas JSON Assemblée nationale
│   ├── import_dossier.py                 # Import direct des liasses d'un dossier législatif
│   ├── commissions_resolver.py           # Résolution hors-ligne des commissions et thèmes
│   ├── deputes_resolver.py               # Résolution des auteurs (actifs & historique 1997+)
│   ├── participants_resolver.py          # Participants d'un texte par groupe et rôle
│   ├── textes_resolver.py                # Résolution locale des articles de loi de référence
│   ├── data/                             # Référentiels Open Data embarqués (JSON)
│   └── services/
│       ├── deterministic_classifier.py   # Classifieur rapide O(N) (Identiques, Dc, Isolés)
│       ├── golden_reference.py           # Référentiel de jurisprudence témoin JOP 2030
│       ├── rag_store.py                  # Vector Store SQLite persistant & repli BM25/TF-IDF
│       ├── rules_engine.py               # Moteur des 384 règles (Art. 40, Art. 45, Art. 98)
│       ├── hatvp_graph.py                # Graphe local des déclarations HATVP
│       ├── chrono_debunker.py            # Debunker chronologique des scrutins/interventions
│       ├── batch_job_queue.py            # File de jobs batch GPU (/api/v2/jobs/*)
│       ├── analysis/                     # Analyse de surtransposition UE
│       └── legal_ingestion/              # Connecteurs EUR-Lex / Légifrance & indexeur local
├── src/                                  # Frontend React 19 + Vite + Tailwind CSS
│   ├── App.jsx                           # Orchestration générale, layout max-w-[1440px], modales
│   ├── api/                              # Clients HTTP compressés & serveur local
│   ├── components/                       # Tableau, détail, comparateur, réglages IA, démo guidée
│   ├── utils/                            # Export RTF Préjaune, export Éloi JSON, crypto AES-GCM, tri
│   ├── data/                             # Jeu d'exemple JOP 2030 & fixtures conformité UE
│   └── __tests__/                        # Suite de 44 tests unitaires Vitest
├── scripts/                              # Outils CLI (voir scripts/README.md)
│   ├── ingest_corpus.py                  # CLI d'ingestion SQLite (--rules, --hatvp, --history, --docs)
│   ├── construire_deputes_historique.py  # Générateur du référentiel AMO30 (1997+)
│   └── generate_demo_audio.py            # Générateur des 15 MP3 de la Démo Guidée
├── docs/                                 # Documentation technique
│   └── DATA_MAPPING_TRICOTEUSES.md       # Cartographie relationnelle des JSON Assemblée nationale
├── reports/                              # Jeux de référence & non-régression
│   └── temoin_classification_golden.json # Golden Dataset JOP 2030 (100 % concordance)
├── tests/                                # Suite de 165 tests Pytest backend & intégration
├── mcp_server.py                         # Serveur MCP Python (7 outils souverains)
├── Dockerfile                            # Image multi-stage Air-Gap (Vite + Python 3.12)
├── docker-compose.yml                    # Stack souveraine Bourbon.IA + Ollama
├── vercel.json                           # Déploiement Vercel & en-têtes HTTP de sécurité
├── SECURITY.md                           # Politique de sécurité, Air-Gap & anti-SSRF
└── ARCHITECTURE.md                       # Schémas techniques détaillés v2.0
```

---

## ⚙️ Installation & Démarrage Rapide

### Option 1 : Exécution locale (Python 3.11+ & Node.js 20+)

```bash
# 1. Cloner le dépôt et préparer la configuration
git clone https://github.com/Justinbdna/bourbon-ia.git
cd bourbon-ia
cp .env.example .env

# 2. Backend FastAPI (port 8000)
python3 -m venv .venv
source .venv/bin/activate        # Sous Windows PowerShell : .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn api.index:app --reload --port 8000

# 3. Frontend React / Vite (port 5173) dans un second terminal
npm install
npm run dev
```

Pour activer l'IA locale souveraine, démarrez [Ollama](https://ollama.com/) (`ollama pull mistral` et `ollama pull bge-m3`) ou [LM Studio](https://lmstudio.ai/) sur `127.0.0.1`, puis sélectionnez **Local** dans **Réglages IA**.

### Option 2 : Conteneurisation Air-Gap (Docker + Ollama)

```bash
docker compose up --build
```

L'application web et l'API sont servies sur `http://localhost:8000`, adossées au service `ollama` (`http://ollama:11434`) avec persistance de la base SQLite dans le volume `/app/data` et `BOURBON_TEXTES_DISTANTS=0`.

### Option 3 : Serveur MCP local (`mcp_server.py`)

```bash
python3 mcp_server.py
```

### CLI d'ingestion du corpus (`scripts/ingest_corpus.py`)

```bash
# Vérifier l'état de la base bourbon_rag.db
python3 scripts/ingest_corpus.py --status

# Ingérer des règles, déclarations HATVP, scrutins et documents juridiques hors-ligne
python3 scripts/ingest_corpus.py --rules data/regles.json --hatvp data/hatvp.csv --history data/scrutins.json --docs data/corpus/
```

Consultez [scripts/README.md](scripts/README.md) pour la documentation complète des scripts.

---

## 🧪 Vérifications & Tests

```bash
# Backend : 165 tests Pytest (erreurs de dépréciation strictes)
python3 -m pytest -W error::DeprecationWarning

# Frontend : 44 tests Vitest
npm test -- --run

# Linter & Build de production
npm run lint
npm run build
```

---

## 🔒 Sécurité & Souveraineté

Consultez [SECURITY.md](SECURITY.md) pour les garanties **Air-Gap**, la protection **anti-SSRF**, le chiffrement navigateur **AES-GCM**, la politique de signalement des vulnérabilités et les en-têtes HTTP de sécurité.
