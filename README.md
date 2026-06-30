# Bourbon.IA 🏛️

**Bourbon.IA** est un Assistant Législatif 100 % Local, développé dans le cadre du hackathon de l'Assemblée nationale.

## 🎯 Le Défi
L'usage d'outils d'IA générative grand public par les équipes parlementaires pose un risque critique de souveraineté. 
**Bourbon.IA** apporte une solution : un copilote totalement hors-ligne qui ingère le flux massif des amendements pour assister les députés et leurs collaborateurs, garantissant une confidentialité totale.

## ✨ Fonctionnalités Principales (MVP)
1. **Le Scanner** : Résumé instantané des enjeux juridiques et politiques d'un amendement.
2. **Le Comparateur** : Mise en évidence visuelle (façon *diff*) des nuances entre l'article de loi initial et l'amendement modificateur.
3. **Le Sourçage Strict (RAG)** : Zéro tolérance pour les hallucinations. Chaque réponse génère un tag cliquable pointant vers la ligne exacte du texte source. 

## 🛠️ Stack Technique
- **Front-End** : React.js (Vite)
- **Back-End** : Python (FastAPI)
- **IA Locale** : Modèle Open Source via **LM Studio** (ou Ollama) en local.
- **Data** : Protocole MCP pour exposer les JSON de l'Assemblée nettoyés au LLM.

## 🚀 Lancement (En cours de développement)
1. Nettoyage des données JSON.
2. Lancement du backend FastAPI.
3. Démarrage de l'application React.
