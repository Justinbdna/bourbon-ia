# AUDIT MVP : BOURBON.IA - TRAITEMENT ET CLASSEMENT SOUVERAIN DES AMENDEMENTS

## 1. Pipeline de Traitement
Le MVP repose sur l'ingestion d'un lot de vrais amendements (JSON) issus de l'open data de l'Assemblée nationale. Le traitement s'effectue en deux étapes complémentaires : un tri mécanique (déterministe, robuste et rapide) opéré par Python, suivi d'une analyse sémantique (IA) ciblée uniquement sur les subtilités du texte.

## 2. Étape 1 : Le Tri Mécanique (Python)
L'algorithme de classement déterministe applique strictement la doctrine parlementaire ("Théorie du classement"). Il parse le "chapeau" des amendements pour identifier le verbe d'action et la cible (article, alinéa). 
L'ordre hiérarchique absolu est respecté lors du tri :
1. **Suppression de l'article** : Si voté, fait tomber tout le reste.
2. **Rédaction globale de l'article**.
3. **Suppression de l'alinéa**.
4. **Rédaction globale de l'alinéa**.
5. **Point d'impact plus restreint** (mot, phrase...).

Cette étape garantit que le traitement respecte la procédure législative et déleste l'IA d'une tâche de classement algorithmique pour laquelle elle n'est pas fiable.

## 3. Étape 2 : L'Analyse Sémantique (LLM Local)
Une fois le lot trié mécaniquement, le LLM (ex: Mistral 7B) est sollicité pour comprendre le fond (le "corps") des amendements. Son rôle strict est la détection d'anomalies :
- **Détection des Identiques** : Repère les amendements dont le texte modificatif est similaire mais dont les auteurs diffèrent (statut recevable, regroupement).
- **Détection des Doublons** : Repère les amendements au corps identique et provenant du même auteur (statut irrecevable).
- **Incompatibilités de Fond** : Identifie les amendements dont la philosophie est diamétralement opposée, signalant une "chute par incompatibilité" si le premier est adopté.

## 4. Validation
Les statuts ("Identique", "Doublon", "Incompatible", "Nouveau") sont retournés par l'API pour validation par l'administrateur dans l'interface Front-End avant l'export définitif. Le juge humain (ou l'administrateur de commission) conserve toujours la main.
