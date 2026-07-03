# 🏛️ HACKATHON BOURBON.IA - RAPPORT D'ÉTAT DES LIEUX

## 1. Architecture Réseau Actuelle
- **Serveur Back-End** : FastAPI (Python) tournant sur `localhost:8000`.
- **Interface Front-End** : React.js (Vite) tournant sur `localhost:5173`.
- **Réseau Local & Privé (Air-Gapped)** :
  - **Mac (Local)** : Modèles exécutés en local via LM Studio pointant sur `http://127.0.0.1:1234/v1`.
  - **PC Gamer (Distant)** : Routage dynamique via **Tailscale** sur l'IP `http://100.78.180.81:1234/v1` pour les modèles plus lourds.
- **Protocoles** : Requêtes REST JSON pour l'interface API, flux HTTP SSE (Server-Sent Events) pour le streaming temps réel.

## 2. État du Back-End (✅ 95% achevé)
Le moteur principal est robuste et opérationnel.
- **Streaming SSE** : L'intégration complète d'OpenAI compatible avec LM Studio fonctionne. Les tokens sont générés en temps réel.
- **Gestion des Fichiers** : L'API peut assimiler le contexte textuel brut de fichiers JSON multiples injectés depuis le Front-End.
- **Base de Données / MCP** : Le contournement réussi de l'erreur 406 du serveur distant MCP. Un endpoint de fallback (`/api/tricoteuses_mock`) agit en RAG sur notre base locale (`amendements_clean.json`), récupérant les *vraies* données de l'Assemblée nationale avec un statut HTTP 200 garanti.
- **Routage Dynamique** : Le dictionnaire de modèles dans le `.env` et `main.py` gère sans faute le dispatching des requêtes entre le Mac et le PC.

## 3. État du Front-End (⚠️ 50% achevé - MVP Brut)
L'interface est fonctionnelle mais accuse un retard sur le rendu visuel (UX/UI).
- **Fonctionnalités validées** :
  - Historique de discussion propre (système de bulles Chat).
  - Gestion de la sélection multi-fichiers avec prévisualisation (attribut `multiple`).
  - Rendu Markdown intégré (`react-markdown`).
  - L'effet de streaming en temps réel avec état "Recherche en cours..." dynamique.
- **Limites visuelles actuelles (Bilan honnête)** :
  - Design trop brut et générique (fond sombre basique).
  - Manque de micro-interactions fluides et de thématique "Assemblée nationale / Premium".
  - Pas d'auto-scroll automatique lors du streaming de longs textes.

## 4. Estimation de l'Avancement
**Taux d'achèvement global estimé : 75%**
- ⚙️ **Moteur & Logique (Back-End / IA)** : **95%**
- 🎨 **Interface & Expérience (Front-End)** : **50%**

### 🚨 Bugs Potentiels et Risques (À sécuriser)
- **Surcharge de la Context Window** : Si un juge (ou utilisateur) sélectionne 10 fichiers JSON volumineux, le modèle `Mistral` (limité à ~8k ou 32k tokens) crashera ou tronquera la requête avec une erreur `max_tokens`.
- **Délai d'Inférence (Timeout)** : Sur le PC distant (Qwen 32B), un premier prompt très lourd peut mettre du temps à démarrer. L'interface React pourrait tomber en *timeout* si la connexion HTTP coupe avant le premier chunk SSE.
- **Faux-Positifs du RAG** : Si l'utilisateur pose une question mal formulée, le mock local pourrait "matcher" le premier amendement par défaut. Il faudra peut-être une fallback plus fine.

## 5. Feuille de Route (Next Steps - Focus Design & UX)
Pour les 2 derniers jours du Hackathon, le Back-End est figé. Toute l'énergie doit aller sur l'UI :
- [ ] **Thématisation "Souveraineté/Premium"** : Adopter un style Glassmorphism, couleurs tricolores subtiles (Bleu/Blanc/Rouge sombres ou teintes Marianne).
- [ ] **Auto-Scroll-To-Bottom** : Implémenter une référence (`useRef`) pour scroller automatiquement la vue en bas lors du streaming.
- [ ] **Limitateur de fichiers** : Côté React, ajouter un avertissement ou bloquer l'envoi si le poids cumulé des fichiers JSON dépasse 20 Ko (afin d'éviter les crashs de contexte).
- [ ] **Bouton Stop** : Implémenter un contrôleur `AbortController` visuellement accessible pour stopper une génération trop bavarde.
- [ ] **Nettoyage du code mort** : Supprimer définitivement les imports inutilisés ou les variables de type `thinkStatus`.
