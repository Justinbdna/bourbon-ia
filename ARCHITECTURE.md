# 🏛️ BOURBON.IA - Architecture & Guide Intégral

Ce document est le pilier technique de Bourbon.IA, l'assistant législatif souverain conçu pour le hackathon de l'Assemblée nationale.

---

## 1️⃣ LE CONCEPT
Bourbon.IA adopte une approche **hybride "Air-Gapped"** garantissant 100% de souveraineté :
- **Tri Algorithmique Infaillible (Python) :** Avant toute analyse sémantique, un moteur déterministe (`sorting_engine.py`) classe les amendements en respectant scrupuleusement la *Théorie du classement* de l'Assemblée (1. Suppression de l'article > 2. Rédaction globale > 3. Alinéas). L'IA ne peut jamais outrepasser ou halluciner cette hiérarchie légale.
- **Analyse Sémantique (LLM Local) :** Un processeur IA léger (`llm_processor.py` couplé au point d'entrée FastAPI) identifie exclusivement les relations complexes : Doublons (même auteur, même fond), Amendements identiques (auteurs différents), et Incompatibilités (chutes).

L'architecture est un monolithe assumé pour itérer rapidement durant ce sprint.

---

## 2️⃣ INSTALLATION & DÉPENDANCES

**Prérequis :**
- Python 3.10+
- Node.js 18+
- LM Studio / Ollama (Port `1234`) avec un modèle chargé (ex: Mistral 7B Instruct).

**Dépendances Backend (Python) :**
- `fastapi`, `uvicorn`, `pydantic` (Pour l'API REST asynchrone).
- `openai` (Pour dialoguer avec le serveur local LM Studio via le standard OpenAI).

**Lancement du Serveur Backend (FastAPI) :**
```bash
# Activation de l'environnement virtuel et installation
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Lancement (port 8000)
uvicorn backend.app.main:app --reload
```

**Lancement du Serveur Frontend (React/Vite) :**
```bash
# Installation et lancement (port 5173)
npm install
npm run dev
```

---

## 3️⃣ LE FLUX LOGIQUE (DATA FLOW)
Voici le parcours exact d'une analyse massive d'amendements :
1. **Upload & Parsing (React) :** L'utilisateur glisse un fichier JSON brut de l'Assemblée. `App.jsx` parse le JSON et extrait un tableau d'objets.
2. **Transfert (HTTP POST) :** React envoie le payload `{ "amendements": [...], "model": "..." }` vers `POST /api/analyze`.
3. **Réception (FastAPI) :** Le modèle Pydantic valide la structure des données de façon stricte.
4. **Moteur de tri (Python) :** `sorting_engine.py` applique la doctrine de l'Assemblée et trie mécaniquement la liste.
5. **Préparation du contexte (LLM Processor) :** Pour éviter la surcharge mémoire (`n_keep > n_ctx`), FastAPI utilise `extraire_texte_brut()` pour tronquer et nettoyer les balises HTML, gardant uniquement l'auteur, le dispositif et l'exposé.
6. **Inférence & Sécurisation (LLM) :** Le texte est envoyé au modèle via LM Studio. Le retour est scanné par une **expression régulière stricte** (`re.search(r'\[.*\]|\{.*\}')`) pour prévenir les crashs liés au formatage capricieux de l'IA. Un `try/except` agit comme fallback ultime.
7. **Interruption asynchrone :** À chaque itération, le backend vérifie `await request.is_disconnected()`. Si l'utilisateur clique sur "Stop", la boucle s'interrompt instantanément.
8. **Rendu (React) :** FastAPI retourne le JSON structuré final. React affiche visuellement les badges (Doublon 🔴, Identique 🟠, Nouveau 🟢).

---

## 4️⃣ INVENTAIRE DES FICHIERS (CORE MVP)

| Fichier / Dossier | Rôle Technique |
| :--- | :--- |
| **`backend/app/main.py`** | Cœur du serveur API. Expose `POST /api/analyze`, orchestre le tri, l'extraction, et la boucle LLM asynchrone avec gestion de l'interruption (Stop). |
| **`backend/llm_processor.py`** | Librairie utilitaire contenant `extraire_texte_brut()` (parsing anti-surcharge) et la configuration réseau du LLM (`resolve_model_and_url()`). |
| **`backend/sorting_engine.py`** | Moteur déterministe appliquant la hiérarchie légale (Théorie du classement) par regex sur les chapeaux d'amendements. |
| **`src/App.jsx`** | Composant React principal. Gère l'upload, la requête `fetch()` asynchrone stricte, et le rendu Markdown visuel. |
| **`backend/requirements.txt`** | Liste stricte des paquets Python nécessaires (FastAPI, Uvicorn, OpenAI). |
| **`.env`** | Configuration réseau locale (`LLM_API_URL`). |

---

## 5️⃣ ROADMAP DU SPRINT FINAL
- [ ] Remplacement de l'interface actuelle par l'intégration HTML/CSS finale (Thème Institutionnel).
- [ ] Câblage visuel avancé des badges dynamiques (Doublon, Identique, Valide) directement dans l'interface de tri.
- [ ] Démonstration live sur le jeu d'essai "crash-test" final de 50 amendements complexes.
