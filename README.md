# 🇫🇷 Bourbon.IA — L'Assistant Législatif 100 % Local

**🔗 Démonstration en ligne :** [bourbon-ia.vercel.app](https://bourbon-ia.vercel.app)

---

## 🎯 Le Défi : L'enfer des 48 heures et la Souveraineté

Grâce à l'expertise métier d'un administrateur de l'Assemblée nationale présent dans notre équipe, nous avons ciblé le vrai blocage : le traitement de volumes écrasants d'amendements dans des délais inhumains. Lors de la réforme des retraites en 2023, **20 400 amendements** ont dû être triés, classés et analysés en **moins de 48 heures** par les équipes parlementaires.

Pour des questions de **confidentialité absolue**, l'usage d'IA Cloud classiques (OpenAI, Anthropic, etc.) est strictement interdit sur les textes législatifs en cours d'examen. Il fallait une solution **"Air-Gapped"** : une IA souveraine, locale, déconnectée d'Internet, capable de tourner intégralement sur les machines de l'Assemblée.

Bourbon.IA est cette solution.

---

## 💡 La Solution & Architecture (MVP V1)

### Edge Computing — Pré-tri Front-End
L'interface React gère l'import de multiples fichiers JSON (format officiel de l'Assemblée nationale) et effectue un **tri mécanique instantané** (doublons stricts, détection par regex du dispositif) directement dans le navigateur. Ce pré-tri déterministe économise les ressources IA en ne transmettant au LLM que les amendements réellement ambigus.

### Sécurité & Architecture — Monolithe Assumé
Pour les besoins du Hackathon, le prototype est un monolithe volontaire. Ce choix d'architecture favorise la vélocité d'itération et la démonstration rapide.

> **🔒 Garantie de sécurité :** Les clés API (utilisées uniquement pour la démo publique) sont strictement stockées côté client (`localStorage` du navigateur) et **ne sont jamais transmises ni sauvegardées sur nos serveurs**. Aucune donnée législative ne transite vers un tiers.

Pour une mise en production, l'architecture évoluera vers des **Micro-services conteneurisés** (Docker/K8s) avec chiffrement de bout en bout.

### Moteur LLM — Bonsai 27B
L'application est configurée pour fonctionner en local avec des modèles surpuissants et quantifiés. Notre configuration de référence :

| Modèle | Paramètres | Usage recommandé |
|---|---|---|
| **Bonsai 27B** (Q4) | 27 milliards | Modèle de référence. Excellent ratio VRAM/Performances. |
| **Mistral 7B Instruct v0.3** | 7 milliards | Rapide et efficace pour les tâches de classification simples. |
| **Qwen 3.5 9B** | 9 milliards | Très bon compromis pour les machines avec < 12 Go VRAM. |
| **Gemma 4 12B** | 12 milliards | Solide pour le raisonnement logique. |
| **QWQ 32B** | 32 milliards | Pour les configurations très haut de gamme (Nécessite > 16 Go VRAM). |

L'intégration de l'API Cloud **Groq** (Llama 3.3 70B) n'est présente que pour assurer la fluidité de la démonstration publique, dans l'attente du déploiement d'une infrastructure GPU souveraine.

---

## 🚀 Roadmap Technique (V2)

- **Connexion MCP (Model Context Protocol) :** Branchement direct sur les flux de données de l'Assemblée nationale pour aspirer les amendements en temps réel, sans import manuel.
- **DeepSeek OCR :** Ingestion et structuration automatique des anciens amendements scannés ou au format PDF non-exploitable.
- **Recherche Sémantique (RAG) :** Déploiement de Qdrant et AnythingLLM pour interroger l'historique législatif complet de l'Assemblée et sourcer chaque réponse de l'IA avec des références exactes.
- **Architecture Micro-services :** Séparation du moteur de tri, du serveur LLM et de l'API Gateway dans des conteneurs indépendants pour la scalabilité et la résilience.

---

## ⚙️ Installation & Lancement

### Prérequis
- **Node.js 18+** et **npm**
- **Python 3.10+** (pour le backend FastAPI)
- **LM Studio** (pour le mode IA locale, sur le port `1234`)

### Front-End (React / Vite)
```bash
# Installer les dépendances
npm install

# Lancer le serveur de développement (port 5173)
npm run dev
```

### Back-End Python (FastAPI)
En production (sur Vercel), le backend tourne de manière autonome et Serverless. En environnement local, il est impératif de lancer le serveur manuellement :

```bash
# Optionnel : activer un environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Lancer le serveur (port 8000)
uvicorn api.index:app --reload
```

### LLM Local (LM Studio)
1. Installer [LM Studio](https://lmstudio.ai/)
2. Charger un modèle (ex: Bonsai 27B, Mistral 7B, Qwen 2.5)
3. Démarrer le serveur local sur le port `1234`
4. **Activer le CORS** dans les paramètres du serveur LM Studio
5. Dans Bourbon.IA, ouvrir les ⚙️ Réglages IA et sélectionner "IA Locale"

---

## 👥 L'Équipe

| Rôle | Nom |
|---|---|
| **Porteur de projet** | Justin Bandiola |
| **Expertise métier** | Un administrateur de l'Assemblée nationale |
| **Contributeurs** | Yassine Yamani, Ralph Ferghali, Basile Nordmann, Sahel Salimi, Anwar Labib, Claudia Trujillo, Nicaise CHOUNGMO FOFACK |

---

*Hackathon Assemblée nationale 2025 — Équipe Bourbon.IA*
