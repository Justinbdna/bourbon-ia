### Nom du défi
Bourbon.IA : L'Assistant Législatif 100 % Local

### Description courte
Bourbon.IA est l'assistant législatif 100% local qui résout le point de douleur n°1 des administrateurs : le tri et le classement des amendements avant leur publication, dans le respect absolu de la déontologie et de la souveraineté numérique.

### Porteur
Justin Bandiola

### Description longue
**Le Constat Terrain : L'enfer des 48 heures**
En 2023, la réforme des retraites a généré un volume record de plus de 20 400 amendements (stratégie d'obstruction). Face à ce mur, un effectif extrêmement réduit d'administrateurs transpartisans doit accomplir un travail titanesque : traiter, trier et classer ce volume écrasant en moins de 48 heures pour alimenter le logiciel de l'Assemblée, *Éloi*.

**La Faille de l'IA Actuelle (L'Insight Métier)**
Grâce à un administrateur de l'Assemblée nationale présent dans notre équipe, nous avons identifié le vrai blocage métier. Pour des questions strictes de déontologie, les administrateurs **ne peuvent pas** utiliser d'IA cloud (ni même les IA publiques d'État) pendant ces 48h, car les amendements ne sont pas encore rendus publics. Les outils IA classiques sont donc inutilisables au moment précis où le besoin est le plus critique.

**La Solution : Bourbon.IA**
Bourbon.IA comble cette faille. C'est un copilote 100 % local (Air-Gapped) qui intervient *avant* la publication, transformant une tâche chronophage et rébarbative en un processus automatisé et souverain :
- **Le Scanner (tri déterministe, sans IA) :** identiques, doublons (même texte, même auteur, même commission), irrecevabilités (Art. 40 financière, Art. 45/98 cavalier ou entonnoir), gage financier et amendements isolés sont détectés instantanément, puis ordonnés selon l'ordre parlementaire (avant/sur l'article, articles bis/ter, sous-amendements rattachés à leur amendement).
- **Le Comparateur (IA) :** sur les seuls cas ambigus, l'IA identifie les discussions communes et les amendements similaires, avec un garde-fou qui rejette tout rapprochement inventé. Elle résume aussi chaque amendement en une ou deux phrases neutres, à la demande.
- **Le contexte législatif en direct :** texte de l'article visé récupéré automatiquement, commission saisie et thèmes du périmètre, groupe politique des auteurs, députés participants au texte, analyse de conformité européenne (surtransposition).
- **Action Directe (UI) :** suppression des doublons en un clic, masquage des amendements écartés, recherche par thème et par auteur, export au format préjaune (RTF) pour alimenter Éloi.

**Roadmap Technique**
Pour le Hackathon, l'application complète (interface et serveur) est déployée sur Vercel. Afin que le jury puisse la tester sans installation, la démo publique utilise Groq (Llama 3.3) sur des amendements **déjà publics** : ce mode n'est pas souverain, et l'application l'annonce avant chaque envoi. En usage réel à l'Assemblée, Bourbon.IA tourne **intégralement en local** (LLM via LM Studio ou Ollama, textes de référence en fichiers locaux) : aucune donnée ne quitte le poste. Si la solution est adoptée, notre équipe s'engage à faire évoluer ce prototype monolithique vers une architecture de production professionnelle (micro-services, conteneurisation Docker).

### Image principale
![Image principale](images/cover.png)

### Contributeurs
- Justin Bandiola
- Yassine Yamani
- Claudia

### Ressources utilisées

- [ ] `openfisca-france-parameters` — Base de données de paramètres ✺ OpenFisca
- [x] `an-dossiers-legislatifs` — Dossiers législatifs de l'Assemblée nationale (législature courante) ✺ Assemblée nationale
- [x] `an-amendements-xvii` — Amendements déposés à l'Assemblée nationale (législature actuelle) ✺ Assemblée nationale
- [ ] `an-comptes-rendus` — Comptes rendus de la séance publique à l'Assemblée nationale (législature actuelle) ✺ Assemblée nationale
- [ ] `an-votes-xvii` — Votes des députés (législature actuelle) ✺ Assemblée nationale
- [x] `an-deputes-en-exercice` — Députés en exercice ✺ Assemblée nationale
- [ ] `an-deputes-historique` — Historique des députés ✺ Assemblée nationale
- [ ] `an-deputes-senateurs-ministres-par-legislature` — Députés, sénateurs et ministres d'une législature ✺ Assemblée nationale
- [ ] `an-agenda-reunions` — Agenda des réunions à l'Assemblée nationale (législature courante) ✺ Assemblée nationale
- [ ] `an-questions-gouvernement` — Questions de l'Assemblée nationale au Gouvernement ✺ Assemblée nationale
- [ ] `an-questions-gouvernement-ecrites` — Questions écrites de l'Assemblée nationale au Gouvernement ✺ Assemblée nationale
- [ ] `an-questions-gouvernement-orales` — Questions orales de l'Assemblée nationale au Gouvernement ✺ Assemblée nationale
- [ ] `premier-ministre-legi` — Codes, lois et règlements consolidés ✺ Premier ministre
- [ ] `premier-ministre-dole` — Dossiers législatifs Légifrance ✺ Premier ministre
- [ ] `premier-ministre-jorf` — Édition ''Lois et décrets'' du Journal officiel ✺ Premier ministre
- [ ] `senat-dispositifs-textes` — Dispositifs des textes déposés ou adoptés au Sénat ✺ Sénat
- [ ] `senat-dossiers-legislatifs` — Dossiers législatifs du Sénat ✺ Sénat
- [ ] `senat-amendements` — Amendements déposés au Sénat ✺ Sénat
- [ ] `senat-senateurs` — Sénateurs ✺ Sénat
- [ ] `senat-questions-gouvernement` — Questions orales et écrites du Sénat au Gouvernement ✺ Sénat
- [ ] `senat-comptes-rendus` — Comptes rendus de la séance publique au Sénat ✺ Sénat
- [ ] `an-et-co-database-regroupement-toutes-donnees` — Base de données unifiée Parlement / Législation / Service Public ✺ Assemblée nationale & communauté
- [ ] `an-et-co-serveur-mcp-regroupement-toutes-donnees` — Serveur MCP  - Accès unifié Parlement / Législation / Service Public ✺ Assemblée nationale & communauté
- [ ] `an-et-co-api-regroupement-toutes-donnees` — API - Accès unifié Parlement / Législation / Service Public ✺ Assemblée nationale & communauté
- [ ] `legiwatch-api-parlement` — API Parlement ✺ LegiWatch
- [ ] `legiwatch-database-parlement` — Base de données Parlement ✺ LegiWatch
- [ ] `legiwatch-serveur-mcp-parlement` — Serveur MCP Parlement ✺ LegiWatch

### 🎬 Démonstration Vidéo
[![▶️ Voir la Démonstration Vidéo Bourbon.IA](images/01-accueil.png)](https://drive.google.com/file/d/1qQ96TeCVFPa59oXvuGqRI4gyOHlKo6OB/view?usp=sharing)

*Cliquez sur l'image ci-dessus pour lire la vidéo de démonstration complète (sur Google Drive).*

### Galerie
![Page d'accueil Bourbon.IA](images/01-accueil.png)
![Interface de travail - Mode Sombre](images/02-interface-sombre.png)
![Interface de travail - Mode Clair](images/03-interface-claire.png)
![Modale de configuration IA locale](images/04-reglages-ia.png)
![Résultats du classement automatique](images/05-resultats-classement.png)

### Documents
- [Diapositives de présentation Bourbon.IA](docs/bourbon.ia.pdf)

### URL de démonstration
https://bourbon-ia.vercel.app/

**Note sur l'infrastructure :** Pour des raisons de puissance de calcul et d'accessibilité publique lors de l'évaluation, la démo en ligne utilise l'IA Groq (Llama 3.3) via une architecture Serverless Vercel. Toutefois, le code de Bourbon.IA est conçu pour être 100 % souverain et peut être exécuté intégralement en local, sans aucune connexion à Internet. Les données parlementaires (textes de loi, députés) proviennent des données ouvertes de l'Assemblée nationale, via l'API Tricoteuses.
