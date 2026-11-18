# Bourbon.IA

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![MCP](https://img.shields.io/badge/MCP-7%20outils-111827)](api/mcp_server.py)
[![Docker Air-Gap](https://img.shields.io/badge/Docker-Air--Gap-2496ED?logo=docker&logoColor=white)](docker/Dockerfile)
[![Pytest](https://img.shields.io/badge/Pytest-165%20tests-22C55E)](tests)
[![Vitest](https://img.shields.io/badge/Vitest-44%20tests-22C55E)](src/__tests__)

Assistant légistique hors-ligne (Air-Gap) conçu pour trier, classer et vérifier des liasses d'amendements parlementaires avant leur publication officielle, sans envoyer de textes confidentiels vers des services cloud.

---

## Genèse : du Hackathon de l'Assemblée nationale à la v2.0

Le projet est né les 3 et 4 juillet 2026 à l'Hôtel de Lassay, lors du [Hackathon 2026 de l'Assemblée nationale](https://hackathon2026.assemblee-nationale.fr/defis/de85f219-55ec-4ec4-94e0-ea61a4794dda) (*« Le parcours de la loi : vers une IA de confiance »*, table S6, avec l'appui des ressources open data parlementaires et de la cellule LexImpact).

En échangeant sur place avec un administrateur de l'Assemblée, un blocage très concret est apparu :

1. **La fenêtre des 48 heures.** Lorsqu'une liasse massive arrive — comme les plus de 20 400 amendements déposés sur la réforme des retraites en 2023 — une petite équipe d'administrateurs transpartisans doit dédoublonner, ordonner et regrouper les amendements en moins de 48 heures pour préparer le **préjaune** (document RTF intermédiaire à crochets) puis alimenter **Éloi** et le **dérouleur** officiel de la séance.
2. **La confidentialité avant séance publique.** Tant que la liasse n'est pas rendue publique, les administrateurs n'ont pas le droit de transmettre ces textes à une API d'IA hébergée dans le cloud, même institutionnelle. Autrement dit, au moment précis où le volume devient ingérable, les assistants IA classiques sont inutilisables.

Pendant le hackathon, nous avions livré un premier prototype monolithique pour valider l'idée (avec un mode de démonstration public sur amendements déjà publiés, encadré par une alerte de consentement). Depuis, Bourbon.IA a été entièrement repris pour devenir une plateforme souveraine utilisable sans accès Internet : le tri par LLM a été remplacé par un moteur déterministe en Python pur fidèle au Règlement de l'Assemblée nationale, complété par une base SQLite locale pour les règles d'irrecevabilité, la transparence HATVP, l'historique des scrutins et la recherche documentaire, ainsi qu'un serveur MCP et une conteneurisation Docker isolée.

---

## Pourquoi une architecture hybride ?

Confiée à un modèle de langage, une liasse de plusieurs centaines d'amendements pose trois problèmes immédiats : c'est lent, le classement change d'une exécution à l'autre, et le modèle tend à inventer des rapprochements ou à ignorer la hiérarchie juridique de l'article 98 du Règlement.

Dans la v2.0, le travail est séparé en deux étages :

| Dimension | Approche tout-LLM cloud | Bourbon.IA v2.0 (hybride & local) |
| :--- | :--- | :--- |
| Temps de traitement (341 amendements) | Plusieurs dizaines de secondes à quelques minutes | **~150 ms** en Python déterministe (mesuré 147–162 ms, seuil CI < 300 ms) |
| Règles de séance (`[Id.]`, `[Dc.]`, Art. 98 RAN) | Probabiliste, non répétable | **100 % déterministe** (120 `[Id.]`, 122 `[Dc.]`, 99 Isolés sur le témoin JOP 2030) |
| Confidentialité avant publication | Envoi des textes vers des serveurs tiers | **Air-Gap par défaut (`BOURBON_TEXTES_DISTANTS=0`)**, exécution locale |
| Usage du LLM (Mistral / Qwen via Ollama ou LM Studio) | Systématique sur toute la liasse | **À la demande uniquement** : résumés en 3 points, cas sémantiques ambigus, surtransposition UE |
| Fiabilité des sources | Risque d'hallucination de références | **Grounding strict** : renvoie `"Information non disponible dans les sources"` sous le seuil |
| Contrôle administrateur | Décision opaque | **Arbitrage manuel** en un clic prioritaire sur l'IA et repris dans les exports |

---

## Ce que fait la v2.0

### Moteur légistique déterministe et exports parlementaires
Le moteur ([api/services/deterministic_classifier.py](api/services/deterministic_classifier.py), [api/deterministic_engine.py](api/deterministic_engine.py) et [api/legal_chapeau_parser.py](api/legal_chapeau_parser.py)) analyse les chapeaux AN/Sénat, normalise la typographie DILA ([api/legal_typography.py](api/legal_typography.py)) et classe instantanément une liasse :
- détection des **Identiques (`[Id.]`)** et **Doublons** en O(N) par empreinte normalisée et similarité de Levenshtein (`> 0,98`) ;
- arbres de décision pour les **Discussions communes (`[Dc.]`)**, y compris le chevauchement de plages d'alinéas ;
- liaison des **amendements tombants** (`tombe_si_adoption_de`) lorsqu'une suppression totale d'article est déposée ;
- calcul de la priorité d'appel en séance selon l'**article 98 du Règlement** (de 1 pour la suppression d'article à 5 pour l'adjonction) ;
- génération native du **Préjaune RTF** avec crochets `╓ ║ ╙` ([api/export_rtf.py](api/export_rtf.py) et [src/utils/exportRtf.js](src/utils/exportRtf.js)) et export JSON compatible **Éloi** ([src/utils/exportEloi.js](src/utils/exportEloi.js)).

### Contrôle approfondi en un clic
Depuis la fiche d'un amendement ([src/components/AmendmentDetail.jsx](src/components/AmendmentDetail.jsx)), le bouton *Lancer l'audit approfondi* interroge trois moteurs locaux adossés à SQLite :
- **Catalogue des 384 règles d'irrecevabilité** ([api/services/rules_engine.py](api/services/rules_engine.py)) : repérage des charges non gagées et gages constitutionnels (**Art. 40 C.**), évaluation de proximité lexicale pour détecter les **cavaliers législatifs** (**Art. 45 C.**), priorité **Art. 98 RAN** et alerte sur les dispositions purement déclaratives (**Art. 6 DDHC**).
- **Graphe d'influence HATVP** ([api/services/hatvp_graph.py](api/services/hatvp_graph.py)) : croisement hors-ligne entre l'amendement, la commission saisie et les déclarations Open Data des représentants d'intérêts.
- **Debunker chronologique** ([api/services/chrono_debunker.py](api/services/chrono_debunker.py)) : mise en regard datée de l'amendement avec les scrutins et interventions passés de l'auteur ou de son groupe, avec repli explicite sur `"Information non disponible dans les sources"` en l'absence d'historique.

### Store RAG SQLite (`bourbon_rag.db`) et repli `/tmp`
[api/services/rag_store.py](api/services/rag_store.py) stocke les chunks documentaires et vecteurs d'embeddings générés localement via `/v1/embeddings` (Ollama `bge-m3` ou LM Studio), avec repli automatique sur un scoring lexical hybride BM25/TF-IDF lorsqu'aucun serveur d'embeddings n'est démarré. Sous `VERCEL=1` ou sur système de fichiers en lecture seule, la base bascule automatiquement vers `/tmp/bourbon_rag.db` (ou le répertoire temporaire OS sous Windows). Aucune réponse n'est inventée : sous `min_score = 0.45`, la requête retourne `no_source` et `"Information non disponible dans les sources"`.

### Interface de travail (`max-w-[1440px]`)
L'application React ([src/App.jsx](src/App.jsx)) affiche le tableau pleine largeur avec tuiles de bilan cliquables, tri parlementaire/chronologique, filtres combinables par article, groupe politique, thème de commission et auteur ([src/components/amendment/AmendmentSearchBar.jsx](src/components/amendment/AmendmentSearchBar.jsx)), comparateur mot-à-mot **Loi initiale vs Amendement** (et entre concurrents) ainsi que l'arbitrage manuel répercuté dans les exports. L'état local du navigateur est chiffré par blocs en AES-GCM ([src/utils/crypto.js](src/utils/crypto.js)).

### Serveur MCP, file batch GPU et Docker
- **Serveur MCP** ([api/mcp_server.py](api/mcp_server.py)) : expose 7 outils sur stdio JSON-RPC / FastMCP (`classer_liasse_mecanique`, `inspecter_amendement`, `rechercher_sources_rag`, `generer_prejaune_rtf`, `evaluer_regles_irrecevabilite`, `verifier_influence_hatvp`, `debunker_historique_acteur`).
- **File de jobs batch GPU** ([api/services/batch_job_queue.py](api/services/batch_job_queue.py)) : traitement par lots jusqu'à `BOURBON_MAX_AMENDEMENTS` (25 000 par défaut) via `POST /api/v2/jobs/submit` et `GET /api/v2/jobs/{job_id}`.
- **CLI d'ingestion** ([scripts/ingest_corpus.py](scripts/ingest_corpus.py)) : pré-chargement hors-ligne des règles, fiches HATVP, scrutins et documents Markdown/JSON dans `bourbon_rag.db`.

---

## Arborescence du dépôt

```text
bourbon-ia/
├── api/                                  # Backend FastAPI, moteurs légistiques & serveur MCP
│   ├── index.py                          # Point d'entrée FastAPI et routes /api/v2/*
│   ├── mcp_server.py                     # Serveur MCP Python (7 outils souverains)
│   ├── schemas.py                        # Modèles Pydantic et plafonds (BOURBON_MAX_AMENDEMENTS)
│   ├── deterministic_engine.py           # Moteur déterministe, sous-amendements, Art. 40/45/98
│   ├── legal_chapeau_parser.py           # Parseur syntaxique des chapeaux AN/Sénat & dérouleur
│   ├── legal_typography.py               # Normalisation typographique DILA
│   ├── export_rtf.py                     # Export Préjaune RTF natif (crochets ╓ ║ ╙)
│   ├── llm_semantic_engine.py            # Client LLM local, anti-SSRF et masquage des clés
│   ├── cache_manager.py                  # Cache RAM TTL
│   ├── transport.py                      # Décompression gzip bornée (50 Mo) & Private Network Access
│   ├── tricoteuses_client.py             # Normalisation des JSON Assemblée nationale
│   ├── import_dossier.py                 # Import des liasses d'un dossier législatif
│   ├── commissions_resolver.py           # Résolution des commissions et mots-clés
│   ├── deputes_resolver.py               # Résolveur députés (actifs et historique depuis 1997)
│   ├── participants_resolver.py          # Participants d'un dossier par groupe et rôle
│   ├── textes_resolver.py                # Résolveur local des articles de référence
│   ├── data/                             # Référentiels Open Data embarqués (JSON)
│   └── services/
│       ├── deterministic_classifier.py   # Classifieur rapide O(N) ([Id.], [Dc.], Isolés)
│       ├── golden_reference.py           # Jurisprudence témoin JOP 2030
│       ├── rag_store.py                  # Store SQLite persistant (RAG + repli /tmp)
│       ├── rules_engine.py               # Moteur des 384 règles (Art. 40, 45, 98, DDHC 6)
│       ├── hatvp_graph.py                # Graphe local des déclarations HATVP
│       ├── chrono_debunker.py            # Debunker chronologique des scrutins/interventions
│       ├── batch_job_queue.py            # File de jobs batch asynchrone (/api/v2/jobs/*)
│       ├── analysis/                     # Détection de surtransposition UE
│       └── legal_ingestion/              # Clients EUR-Lex / Légifrance et indexeur local
├── src/                                  # Frontend React 19 + Vite + Tailwind CSS
│   ├── App.jsx                           # Shell principal (max-w-[1440px]), modales et état
│   ├── api/                              # Clients HTTP compressés & détection serveur local
│   ├── components/                       # Tableau, fiche détaillée, comparateur, démo guidée
│   ├── utils/                            # Exports RTF/Éloi, crypto AES-GCM, tri, sanitization
│   ├── data/                             # Jeu d'exemple JOP 2030 & fixtures UE
│   └── __tests__/                        # 44 tests Vitest
├── scripts/                              # Scripts CLI (indexés dans scripts/README.md)
│   ├── ingest_corpus.py                  # Ingestion SQLite hors-ligne & inspection (--status)
│   ├── construire_deputes_historique.py  # Reconstruction AMO30 (1997+)
│   ├── generate_demo_audio.py            # Génération des 15 MP3 de la démo guidée
│   └── README.md                         # Documentation détaillée des scripts
├── docs/                                 # Documentation technique
│   ├── ARCHITECTURE.md                   # Schémas d'architecture v2.0
│   └── DATA_MAPPING_TRICOTEUSES.md       # Cartographie JSON Assemblée nationale / Tricoteuses
├── docker/                               # Déploiement conteneurisé isolé
│   ├── Dockerfile                        # Image multi-stage (build Vite + Python 3.12)
│   └── docker-compose.yml                # Stack Bourbon.IA + Ollama avec volume persistant
├── reports/
│   └── temoin_classification_golden.json # Jeu témoin de non-régression JOP 2030
├── tests/                                # 165 tests Pytest backend et intégration
├── .env.example                          # Modèle de configuration (Air-Gap par défaut)
├── SECURITY.md                           # Politique de sécurité, Air-Gap et protections anti-SSRF
└── vercel.json                           # Configuration Vercel et en-têtes HTTP de sécurité
```

---

## Installation et démarrage

### En local (Python 3.11+ et Node.js 20+)

```bash
git clone https://github.com/Justinbdna/bourbon-ia.git
cd bourbon-ia
cp .env.example .env

# Backend FastAPI (port 8000)
python3 -m venv .venv
source .venv/bin/activate        # Windows PowerShell : .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn api.index:app --reload --port 8000

# Frontend React / Vite (port 5173) dans un second terminal
npm install
npm run dev
```

Pour utiliser l'IA locale à la demande, lancez [Ollama](https://ollama.com/) (`ollama pull mistral` et `ollama pull bge-m3`) ou [LM Studio](https://lmstudio.ai/) sur `127.0.0.1`, puis vérifiez le mode **Local** dans les réglages de l'application.

### Avec Docker (mode Air-Gap)

```bash
docker compose -f docker/docker-compose.yml up --build
```

Le conteneur démarre avec `BOURBON_TEXTES_DISTANTS=0`, `BOURBON_MAX_AMENDEMENTS=25000` et un volume persistant `/app/data` partagé avec le service `ollama`.

### Serveur MCP et ingestion hors-ligne

```bash
# Démarrer le serveur MCP sur stdio
python3 api/mcp_server.py

# Inspecter ou alimenter la base SQLite locale
python3 scripts/ingest_corpus.py --status
python3 scripts/ingest_corpus.py --rules data/regles.json --hatvp data/hatvp.csv --history data/scrutins.json --docs data/corpus/
```

---

## Tests et qualité

```bash
# Backend (165 tests Pytest)
pytest -W error::DeprecationWarning

# Frontend (44 tests Vitest), linter (oxlint) et build de production
npm test -- --run
npm run lint
npm run build
```

Pour les détails sur le modèle de menace, la configuration `BOURBON_TEXTES_DISTANTS=0` et la protection anti-SSRF, voir [SECURITY.md](SECURITY.md) et [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
