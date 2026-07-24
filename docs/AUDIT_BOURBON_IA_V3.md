# 🏛️ AUDIT DE MATURITÉ ET SÉCURITÉ V3 — BOURBON.IA
> **Date :** 24 Juillet 2026  
> **Contexte :** Retour d'audit externe de sécurité et d'architecture  
> **Objectif :** Anticipation des failles systémiques et consolidation vers une version de production institutionnelle.

---

## 1. Les limites du "100 % Local" actuel : L'illusion de l'Air-Gap

La garantie "100 % local" de notre MVP repose sur l'idée que le LLM tourne sur le poste de l'utilisateur (via LM Studio) et que les requêtes ne quittent pas la machine. Cependant, l'audit externe souligne une faille conceptuelle majeure :

- **Air-Gap Théorique vs Réalité SPA :** L'application React/Vite (SPA) est actuellement servie depuis Vercel. Même si l'inférence est locale, le bundle lui-même (fichiers JS, polices, sourcemaps) nécessite un appel sortant vers Internet. Pour un véritable environnement "Air-Gapped" manipulable pendant les 48 heures critiques, l'application entière doit être servie depuis un intranet de l'Assemblée nationale, sans aucune connexion sortante.
- **Le Risque du CORS Ouvert (DNS Rebinding) :** Actuellement, LM Studio nécessite l'activation d'un CORS permissif pour accepter les requêtes de l'application web. Cette surface d'attaque sur `localhost` ouvre la porte à des vulnérabilités de type "DNS Rebinding". En production, une liste blanche stricte des origines (ex: `https://outils.assemblee-nationale.fr`) doit remplacer le CORS `*` permissif.

---

## 2. L'impératif de la Vérité Terrain (Ground Truth)

Le tri déterministe (Priorités 1 à 4) est mathématiquement robuste car il repose sur des règles de type Regex claires. En revanche, le classement sémantique (détection d'amendements *Identiques* non stricts, ou en *Discussion commune*) délègue un jugement critique à une IA (Bonsai 27B, Qwen 3.5, ou Gemma 4).

- **L'Absence de Benchmark Historique :** Jusqu'à présent, le modèle a été choisi de manière empirique. Il est impératif de confronter le système à une **vérité terrain**.
- **Planification :** Nous devons ingérer le jeu de données historique des **20 400 amendements de la réforme des retraites de 2023** (dont le classement officiel est désormais public et connu) pour mesurer précisément le **taux d'erreur réel** de chaque modèle. La sélection du modèle de production ne doit plus relever de l'intuition, mais d'une validation métrique (Précision, Rappel, F1-Score).
- **Reproductibilité :** Pour qu'une décision d'IA soit juridiquement défendable, la température de l'IA lors des analyses de classement doit être maintenue à 0 afin de garantir la reproductibilité absolue d'un résultat face au même lot.

---

## 3. Gouvernance, Traçabilité et Validation Humaine

Bourbon.IA produit un document (le Préjaune) qui influence directement le dérouleur officiel des débats parlementaires. La traçabilité n'est pas une option.

- **Journalisation Stricte :** À terme, chaque run devra générer des métadonnées infalsifiables : Modèle utilisé exact, version du prompt système, horodatage, et logs de décision. Si un député conteste la mise en "Discussion commune" de son amendement, l'institution doit pouvoir justifier mécaniquement ce choix.
- **Validation Humaine Obligatoire (Human-in-the-Loop) :** Le système de l'Assemblée ne peut accepter d'export automatisé "aveugle". L'interface UI de Bourbon.IA doit intégrer un système de *Check* explicite où un administrateur appose sa signature numérique pour valider le classement proposé par l'IA avant tout export RTF ou JSON vers l'outil souverain *Éloi*.

---

## 4. La Gestion de l'Incertitude : Le péril de la faille silencieuse

Un biais cognitif dangereux entoure l'usage des LLM très compressés ou des petits modèles (7B-32B). 

- **Le Mythe de la certitude :** La pire défaillance d'une IA n'est pas l'erreur, c'est **l'erreur silencieuse**. Un modèle qui crashe ou renvoie un texte incohérent alerte immédiatement l'utilisateur (le badge passe en rouge "Erreur", comme notre UI le gère très bien actuellement). 
- **La Faille Silencieuse :** En revanche, un modèle très compressé qui obéit strictement au format JSON mais qui classe silencieusement deux amendements dissemblables en "Identiques" crée une faille critique sans lever la moindre alerte visuelle.
- **Critère de Sélection :** Le choix final du modèle ne doit pas se baser uniquement sur son "pourcentage de réussite moyen", mais sur son **taux d'erreur silencieuse**. Un modèle plus lent et incertain, mais qui sait demander de l'aide ou s'abstenir (ex: statut *Ambigu - Nécessite Expertise*), est infiniment supérieur à un modèle rapide mais excessivement confiant.

---

> **Conclusion :** Bourbon.IA a atteint le stade de la maturité conceptuelle (MVP fonctionnel, UI réactive, architecture hybride). La V3 doit maintenant s'attaquer à la maturité de **gouvernance** : tester le modèle face à l'histoire, cadenasser les flux réseau, sécuriser l'état local contre les crashs de l'utilisateur (Auto-save implémenté), et assumer que l'IA ne remplacera jamais l'administrateur, mais qu'elle pré-mâchera son travail.
