# Bourbon.IA 🇫🇷

**Assistant législatif 100% local (Hackathon Assemblée nationale)**

Bourbon.IA est un outil souverain, "air-gapped", conçu pour assister les équipes parlementaires dans le tri, le classement et l'analyse sémantique massive d'amendements, sans jamais exposer de données confidentielles à des API Cloud externes.

---

## 🏗️ Architecture (Monolithe Assumé)
Pour favoriser une itération très rapide lors de ce sprint, le projet repose sur une architecture claire et directe :
- **Tri Algorithmique Strict (Python) :** Classement déterministe basé sur la *Théorie du classement* (Suppression > Rédaction > Alinéas) pour préserver la doctrine de l'Assemblée.
- **Analyse Sémantique Heuristique (LLM Local) :** Un processeur IA qui identifie exclusivement les doublons, les amendements identiques et les incompatibilités de fond.
- **Front-End (React/Vite) :** Interface utilisateur moderne (thème institutionnel "Assemblée nationale" / Glassmorphism) pour afficher visuellement les résultats via une route REST directe (`/api/analyze`).

---

## 🚀 Prérequis d'installation
- **Python 3.10+**
- **Node.js 18+**
- **LM Studio** (ou Ollama) tournant sur le port local `1234` avec un modèle chargé (ex: Mistral 7B Instruct).

---

## 🛠️ Démarrer l'environnement

### 1. Démarrer le Back-End (FastAPI)
L'API tourne sur le port `8000`. Depuis la racine du projet :
```bash
# Optionnel mais recommandé : Activer un environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# Installer les dépendances
pip install -r backend/requirements.txt

# Lancer le serveur
uvicorn backend.app.main:app --reload
```

### 2. Démarrer le Front-End (React/Vite)
L'interface UI tourne sur le port `5173`. Dans un nouveau terminal :
```bash
# Installer les dépendances
npm install

# Lancer le serveur de développement
npm run dev
```

---

## 📂 Utilisation & Données de Test
**⚠️ Rappel Important :**  
Les lots de test (fichiers JSON bruts de l'Assemblée) doivent être envoyés au système. L'application parse automatiquement les données profondes (`signataires > auteur`, `corps > dispositif`, etc.) pour optimiser le contexte LLM.
Vous pouvez glisser-déposer vos fichiers JSON directement via l'interface UI (bouton 📎).

---
*Hackathon Assemblée nationale — Équipe Bourbon.IA*
