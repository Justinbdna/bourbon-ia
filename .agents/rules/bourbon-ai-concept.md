---
trigger: always_on
---

# 🚀 CONTEXTE GLOBAL ET DIRECTIVES DE DÉVELOPPEMENT : BOURBON.IA

## 1. VISION ET OBJECTIF DU PROJET
Tu agis en tant que Lead Développeur Senior. Nous développons "Bourbon.IA", un Assistant Législatif 100 % Local conçu pour le hackathon de l'Assemblée nationale française.
Le problème métier : Le traitement chronophage des amendements par les équipes parlementaires et le risque critique de fuite de données (souveraineté).
La solution : Une application web "Air-Gapped" (sans aucune connexion internet sortante vers des API Cloud type OpenAI). L'outil ingère des données ouvertes (fichiers JSON massifs de l'Assemblée) et utilise un LLM open-source en local pour résumer, comparer et sourcer les textes législatifs.

## 2. LA STACK TECHNIQUE DÉFINITIVE
- Front-End : React.js (via Vite) pour une interface réactive et moderne.
- Back-End / API : Python avec FastAPI. Rôle : traiter la donnée pure, nettoyer les JSON, et faire le pont de manière asynchrone.
- Intelligence Artificielle : Ollama exécuté localement (modèles cibles : Mistral ou Qwen).
- Protocole d'Intégration : Model Context Protocol (MCP). Nous allons créer un véritable serveur MCP en Python qui exposera nos données JSON nettoyées comme des "outils" (tools) interrogeables par le LLM.

## 3. LES 3 FONCTIONNALITÉS CLÉS (MVP)
1. LE SCANNER (Analyse et Résumé) : 
L'utilisateur charge un amendement. Le Back-End nettoie le JSON, le passe au LLM via le serveur MCP, et retourne un résumé structuré (enjeux juridiques et politiques) sans jargon inutile.

2. LE COMPARATEUR (Diff visuel) : 
L'interface Front-End affiche côte à côte l'article de loi initial et l'amendement modificateur. Le code doit surligner visuellement (façon GitHub diff) les ajouts en vert et les suppressions en rouge.

3. LE SOURÇAGE STRICT (RAG) : 
Tolérance ZÉRO pour les hallucinations. Chaque réponse générée par le LLM doit inclure des références exactes. L'interface affichera des tags cliquables renvoyant au numéro de l'amendement ou à l'article visé. Si l'information est absente du JSON, le système doit strictement répondre : "Information non disponible dans les sources".

## 4. MÉTHODOLOGIE ET RÈGLES DE CODAGE POUR L'AGENT
En tant qu'assistant de code, tu dois impérativement respecter cette logique procédurale :
- Étape par étape : Ne génère pas toute l'application d'un coup. Nous allons procéder par composants logiques (d'abord l'API FastAPI, puis le nettoyage JSON, puis la connexion Ollama/MCP, puis le Front-End React).
- Optimisation JSON : Les fichiers de l'Assemblée sont très lourds et imbriqués. Propose toujours des scripts Python pour extraire uniquement les clés/valeurs nécessaires (texte, signataires, exposé des motifs) avant de les envoyer au LLM pour économiser des tokens et de la RAM.
- Sécurité et Souveraineté : Ne propose JAMAIS d'installer des librairies ou des SDK pointant vers des services Cloud externes. Tout doit tourner sur `localhost`.
- Gestion des erreurs : Anticipe les crashs du LLM local (timeout, dépassement de contexte) et gère ces erreurs proprement côté FastAPI.

Dès que tu as lu et compris ces instructions, réponds uniquement par : "Contexte Bourbon.IA assimilé. Prêt à initialiser la stack. Par quoi commençons-nous : la création du serveur FastAPI ou le script de nettoyage des fichiers JSON ?"