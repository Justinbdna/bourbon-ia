# 🚀 AUDIT ET FEUILLE DE ROUTE BOURBON.IA - SPRINT DU SAMEDI

## 1. 🏗️ ARCHITECTURE RÉSEAU (RAPPEL DES PORTS)
- **FRONT-END (React/Vite)** : `Port 5173` (Ne fait aucun calcul, affiche juste l'UI).
- **BACK-END (FastAPI)** : `Port 8000` (Routeur logique et connexion DB).
- **MOTEUR IA (LM Studio)** : `Port 1234`.

## 2. 🌐 ADRESSES IP (RÉSEAU TAILSCALE)
- **Serveur Primaire (Mac de secours)** : `http://100.111.208.109:1234/v1`
- **Serveur Cible (PC Gamer Justin)** : `http://100.78.180.81:1234/v1` (À utiliser dès que le pare-feu et le CORS `0.0.0.0` seront débloqués demain matin).

## 3. ⚖️ RÈGLE MÉTIER ABSOLUE (THÉORIE DU CLASSEMENT)
La logique de tri algorithmique prime TOUJOURS sur l'IA. L'ordre de classement des amendements est strict :
1. Suppression de l'article (fait tomber les autres).
2. Rédaction globale de l'article.
3. Suppression de l'alinéa.
4. Rédaction globale de l'alinéa.
5. Point d'impact plus restreint (mot à mot).

## 4. 🧠 RÔLE STRICT DU LLM
Le LLM ne fait pas le classement hiérarchique. Il est utilisé EXCLUSIVEMENT pour :
- Détecter la différence entre un **Doublon** (irrecevable car même auteur) et des **Identiques** (recevables car auteurs différents).
- Détecter les **Chutes par incompatibilité de fond** (contradictions philosophiques ou juridiques entre deux amendements).

## 5. 🎯 MISSIONS PRIORITAIRES DU SAMEDI
- **Yassine (Back-End)** : 
  - Débloquer le pare-feu / CORS du PC Gamer pour pointer sur l'IP Tailscale définitive.
  - Implémenter l'algorithme de tri strict (Théorie du classement) couplé à SQLAlchemy pour traiter les lots d'amendements avant de solliciter le LLM.
- **Justin (Front-End & UI/UX)** : 
  - Sublimer l'interface (thème institutionnel "Assemblée nationale" avec touches de Glassmorphism).
  - Intégrer visuellement le retour structuré du backend (statuts, couleurs d'alerte, justifications).
- **Consolidation Globale** :
  - Connecter de bout en bout l'endpoint `/api/analyze` avec le Front-End.
  - Préparer les données de démonstration finales pour le pitch.
