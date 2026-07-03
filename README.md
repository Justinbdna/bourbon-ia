# Bourbon.IA 🏛️

**Bourbon.IA** est un Assistant Législatif souverain, développé dans le cadre du hackathon de l'Assemblée nationale.

## 🎯 Le Défi
L'usage d'outils d'IA générative grand public (type ChatGPT) par les équipes parlementaires pose un risque critique de souveraineté : les textes de travail transitent par des API cloud tierces, hors de tout contrôle.

**Bourbon.IA** apporte une solution : un copilote qui s'appuie **exclusivement sur des modèles open-source auto-hébergés** — aucun appel vers une API d'IA commerciale (OpenAI, Anthropic, etc.). Le traitement des amendements reste sur une infrastructure maîtrisée par l'institution.

## 🔒 Modèle de souveraineté (à lire)
Pour être précis sur ce que « souverain » signifie ici :

- **Aucun LLM cloud grand public** n'est utilisé. L'inférence tourne sur un serveur compatible OpenAI auto-hébergé (**LM Studio** ou **Ollama**), soit :
  - en **local** sur la machine (`http://127.0.0.1:1234/v1`), soit
  - sur un **PC dédié du réseau local**, joignable via **Tailscale** (voir `LLM_API_URL` dans `.env`).
- **Sourçage des données** : le backend interroge un serveur **MCP** (`backend/mcp_config.json`). Par défaut il pointe vers un endpoint distant (`mcp.code4code.eu`). ⚠️ Pour un déploiement réellement confiné, cet endpoint doit être remplacé par une instance MCP hébergée en interne — sinon les requêtes de recherche sortent vers un tiers.

En résumé : **pas d'IA cloud commerciale**, mais l'architecture actuelle repose sur du réseau (LAN/Tailscale + MCP distant), et n'est pas *air-gapped* au sens strict tant que le MCP interne n'est pas déployé.

## ✨ Fonctionnalités Principales (MVP)
1. **Le Scanner** : Résumé instantané des enjeux juridiques et politiques d'un amendement.
2. **Le Comparateur** : Mise en évidence visuelle (façon *diff*) des nuances entre l'article de loi initial et l'amendement modificateur.
3. **Le Sourçage Strict (RAG)** : Zéro tolérance pour les hallucinations. Chaque réponse génère un tag cliquable pointant vers la ligne exacte du texte source.

## 🛠️ Stack Technique
- **Front-End** : React.js (Vite)
- **Back-End** : Python (FastAPI)
- **IA** : Modèle open-source via **LM Studio** (ou Ollama), auto-hébergé en local ou sur le LAN.
- **Data** : Protocole MCP pour exposer les JSON de l'Assemblée nettoyés au LLM.

## 🚀 Lancement

### Prérequis
- Python 3.10+, Node.js 18+
- Un serveur LLM compatible OpenAI démarré (LM Studio ou Ollama) avec un modèle chargé (ex. Mistral 7B Instruct).

### 1. Configuration
```bash
cp .env.example .env
# Éditez .env pour pointer LLM_API_URL vers votre serveur LLM (local ou Tailscale)
```

### 2. Données
Placez les JSON bruts de l'Assemblée dans `data/raw/`, puis nettoyez-les :
```bash
python3 backend/scripts/parser.py \
  --input-dir data/raw/<DOSSIER> \
  --output data/clean/amendements_clean.json
```

### 3. Back-End (FastAPI)
```bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload   # depuis la racine du dépôt
```

### 4. Front-End (React / Vite)
```bash
npm install
npm run dev
```
