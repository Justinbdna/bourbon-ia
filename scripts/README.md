# Scripts Utilitaires — Bourbon.IA

Ce dossier regroupe les scripts CLI autonomes pour l'ingestion hors-ligne du corpus juridique, la mise à jour des référentiels parlementaires et la génération des ressources média de démonstration.

## Inventaire des scripts

| Script | Rôle | Exécution |
| :--- | :--- | :--- |
| `scripts/ingest_corpus.py` | CLI d'ingestion massive et d'inspection de la base SQLite (`data/bourbon_rag.db` ou `BOURBON_DB_PATH`) : règles d'irrecevabilité, déclarations HATVP, historique des scrutins et corpus documentaire RAG. | `python3 scripts/ingest_corpus.py --status` |
| `scripts/construire_deputes_historique.py` | Construit `api/data/deputes_historique.json` à partir de l'archive Open Data AMO30 de l'Assemblée nationale (tous les députés depuis la XIe législature, 1997). | `python3 scripts/construire_deputes_historique.py <chemin_amo30/json>` |
| `scripts/generate_demo_audio.py` | Génère les 15 fichiers MP3 de la Démo Guidée (`public/audio/demo/etape-01.mp3` à `etape-15.mp3`) avec la voix `fr-FR-DeniseNeural` via `edge-tts`. | `python3 scripts/generate_demo_audio.py` |

---

## Détail : CLI d'ingestion (`scripts/ingest_corpus.py`)

Permet de pré-charger la base SQLite locale sans connexion Internet sortante (mode Air-Gap) :

```bash
# Inspecter le volume actuellement indexé dans les 4 tables SQLite
python3 scripts/ingest_corpus.py --status

# Charger un catalogue de règles d'irrecevabilité (JSON, CSV ou Markdown)
python3 scripts/ingest_corpus.py --rules data/regles_384.json

# Charger des déclarations Open Data HATVP (JSON ou CSV)
python3 scripts/ingest_corpus.py --hatvp data/hatvp_export.csv

# Charger l'historique daté des scrutins et interventions parlementaires
python3 scripts/ingest_corpus.py --history data/scrutins_17e.json

# Indexer un dossier ou fichier documentaire (.md, .txt, .json) dans le store RAG
python3 scripts/ingest_corpus.py --docs data/corpus_juridique/

# Optionnel : calculer les vecteurs d'embeddings locaux via Ollama / LM Studio (/v1/embeddings)
python3 scripts/ingest_corpus.py --docs data/corpus_juridique/ --try-embeddings

# Spécifier un chemin SQLite explicite
python3 scripts/ingest_corpus.py --db-path /chemin/personnalise/bourbon_rag.db --status
```

### Tables SQLite alimentées
1. `rag_chunks` : passages sourcés et vecteurs d'embeddings locaux (ou repli lexical BM25 / TF-IDF).
2. `legislative_rules` : catalogue des règles d'irrecevabilité (Art. 40 C., Art. 45 C., Art. 98 RAN, Art. 6 DDHC).
3. `hatvp_declarations` : fiches des représentants d'intérêts HATVP.
4. `parliamentary_history` : historique daté des scrutins et interventions parlementaires.

---

## Détail : Référentiel historique des députés (`scripts/construire_deputes_historique.py`)

```bash
curl -o amo30.zip https://data.assemblee-nationale.fr/static/openData/repository/17/amo/tous_acteurs_mandats_organes_xi_legislature/AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip
unzip amo30.zip -d amo30
python3 scripts/construire_deputes_historique.py amo30/json
```

---

## Détail : Audio de la Démo Guidée (`scripts/generate_demo_audio.py`)

Nécessite le paquet optionnel `edge-tts` (`pip install edge-tts`). Produit `public/audio/demo/etape-01.mp3` à `public/audio/demo/etape-15.mp3`.
