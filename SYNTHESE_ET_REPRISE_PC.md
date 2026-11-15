# 🏛️ Bourbon.IA — Synthèse de Développement & Guide de Reprise sur PC

> **Document de référence pour reprise immédiate sur machine de développement (PC Gamer / Windows / Linux / macOS)**
> **Dernière synchronisation Git :** Commit `6d5fce0` sur les branches `main` et `feature/legistique-an-senat`.

---

## 🎯 1. Vision & Architecture du Projet

**Bourbon.IA** est un assistant législatif conçu pour l'Assemblée nationale et le hackathon LexImpact.
- **Principe fondamental :** Souveraineté totale et exécution locale **Air-Gapped** (zéro fuite de données vers des API Cloud externes pour les textes d'amendements confidentiels).
- **Stack technique :**
  - **Frontend :** React 18+ (Vite), Tailwind CSS, Lucide Icons, support Mode Clair / Sombre.
  - **Backend / API :** Python 3.11+ avec FastAPI et Uvicorn sur `http://localhost:8000`.
  - **Moteur Déterministe :** Algorithmes parlementaires en Python pur pour les règles de séance (100 % fiable, sans hallucination).
  - **IA Locale :** Intégration Ollama / LM Studio (Mistral 7B / Qwen 2.5) via protocoles locaux compatibles OpenAI / MCP.
  - **Données :** Référentiels ouverts de l'Assemblée nationale (Tricoteuses AMO30, textes de lois consolidés, historique des députés depuis 1997).

---

## 🚀 2. Synthèse Détaillée de Tout ce qui a été Développé

### 🏛️ Axe 1 : Moteur Légistique & Règles de Séance (100 % Fiable)
Fichiers : [`api/deterministic_engine.py`](file:///Users/jujutravail/bourbon-ia/api/deterministic_engine.py), [`api/schemas.py`](file:///Users/jujutravail/bourbon-ia/api/schemas.py), [`api/index.py`](file:///Users/jujutravail/bourbon-ia/api/index.py)

1. **Amendements « Tombants » (Chute par ricochet)** :
   - Détection automatique : lorsqu'un amendement de suppression totale d'article (ex. CD50) est déposé, tous les amendements ultérieurs modifiant des alinéas de cet article deviennent caducs si l'amendement de suppression est adopté.
   - Liaison hiérarchique : `parent_suppression_numero`, `tombe_si_adoption = True`.
   - Affichage visuel d'alerte : pastille `⚠️ Tombe si adoption de CD...` dans le tableau, le volet de détail, et mention explicite dans l'export préjaune RTF.
2. **Ordre d'appel en séance (Art. 98 du Règlement de l'AN)** :
   - Priorité d'appel de 1 à 5 calculée selon le verbe du dispositif :
     - **Score 1 :** Suppression totale de l'article (`priorite_appel == 1`)
     - **Score 2 :** Rédaction globale de l'article (`priorite_appel == 2`)
     - **Score 3 :** Suppression d'alinéas (`priorite_appel == 3`)
     - **Score 4 :** Substitution ou réécriture partielle (`priorite_appel == 4`)
     - **Score 5 :** Insertion ou adjonction (`priorite_appel == 5`)
   - Tri automatique au sein de chaque discussion commune pour afficher l'amendement pivot prioritaire en tête de liste.
3. **Détection des « Cavaliers législatifs » (Article 45 de la Constitution)** :
   - Détection heuristique de cohérence entre l'exposé sommaire et le périmètre du projet de loi.
   - Affichage d'une alerte spécifique : `⚖️ Risque Art. 45 (Lien indirect douteux)`.
4. **Gages financiers (Article 40)** :
   - Repérage des amendements gagés financièrement avec badge doré `💰 Gagé (Art. 40)`.
5. **Gestion des Identiques et Doublons** :
   - Détection mécanique infaillible des amendements strictement identiques (collision d'alinéa et texte normalisé).
   - Détection des doublons redéposés par le même auteur devant la même commission avec bouton de suppression en 1 clic.

---

### 🧠 Axe 2 : IA Locale & Prompt Engineering Chirurgical
Fichiers : [`api/llm_semantic_engine.py`](file:///Users/jujutravail/bourbon-ia/api/llm_semantic_engine.py)

1. **Format de décryptage contraint en 3 points stricts** :
   Le prompt système force le LLM local à restituer une analyse synthétique lisible en 5 secondes par un administrateur :
   - `• Conflit légistique : [Collision sur l'alinéa X entre suppression et substitution]`
   - `• Clivage politique : [Divergence entre le groupe X et le groupe Y]`
   - `• Conséquence du vote : [L'adoption de l'un fait tomber l'autre]`
2. **RAG contextuel d'alinéa cible** :
   - Extraction automatique par regex de l'alinéa ciblé dans le texte de référence (`texte_loi_reference`).
   - Injection directe dans la balise `<ALINEA_CIBLE_INITIAL numero="...">` pour forcer l'IA à citer les termes exacts de la loi existante sans inventer.

---

### 💻 Axe 3 : Interface Utilisateur & Workflow Administrateur
Fichiers : [`src/components/AmendmentTable.jsx`](file:///Users/jujutravail/bourbon-ia/src/components/AmendmentTable.jsx), [`src/components/AmendmentDetail.jsx`](file:///Users/jujutravail/bourbon-ia/src/components/AmendmentDetail.jsx), [`src/components/amendment/AmendmentSearchBar.jsx`](file:///Users/jujutravail/bourbon-ia/src/components/amendment/AmendmentSearchBar.jsx), [`src/App.jsx`](file:///Users/jujutravail/bourbon-ia/src/App.jsx)

1. **Démo guidée avec voix studio institutionnelle MP3** :
   - 17 fichiers audio pré-enregistrés haute qualité situés dans `public/audio/demo/` (voix féminine institutionnelle rappelant la présidence de séance).
   - Mode narrateur interactif synchronisé pas-à-pas avec mise en surbrillance des éléments UI.
2. **Requalification manuelle en 1 clic (Human-in-the-Loop)** :
   - Sélecteur dropdown interactif directement dans la colonne *Statut* du tableau (Discussion commune, Identique, Isolé, Écarté, Doublon).
   - Badge d'audit `✍️ Arbitré` appliqué instantanément dès qu'un statut est corrigé par l'humain.
3. **Comparateur syntaxique mot-à-mot (Word Diff)** :
   - Algorithme LCS de diff pur JS sans dépendance lourde dans `AmendmentDetail.jsx`.
   - Sélecteur *« ⚖️ Comparer avec : »* permettant d'opposer le dispositif d'un amendement à celui d'un concurrent sur le même article.
   - Affichage visuel du diff avec légende claire : mots supprimés en <del>rouge</del> et mots ajoutés en <ins>vert</ins>.
4. **Barre de recherche multi-critères** :
   - 4 filtres croisés en temps réel : **Article**, **Groupe politique**, **Thème de commission**, et **Auteur**, avec décomptes automatiques et tri parlementaire naturel.
5. **Harmonisation UI et résolutions de bugs** :
   - Correction du bug d'espace blanc vide lors du scroll horizontal du tableau.
   - Alignement vertical et centrage parfait des bulles d'impact et du bouton « Retirer ».
   - Bandeau de bilan interactif permettant de filtrer les amendements par catégorie en un clic.

---

### 📋 Axe 4 : Exports & Interopérabilité Hémicycle
Fichiers : [`src/utils/exportEloi.js`](file:///Users/jujutravail/bourbon-ia/src/utils/exportEloi.js), [`src/utils/exportRtf.js`](file:///Users/jujutravail/bourbon-ia/src/utils/exportRtf.js)

1. **Export Éloi (Assemblée nationale / LexImpact)** :
   - Nouveau bouton **`📋 Export Éloi (AN)`** générant un JSON standardisé intégrant métadonnées de séance, ordre d'appel Art. 98, flags tombants, risque Art. 45 et analyse IA.
2. **Export Préjaune RTF** :
   - Format de préjaune parlementaire officiel téléchargeable en `.rtf` intégrant les mentions de chute par ricochet.

---

## 🛠️ 3. Guide de Démarrage sur votre PC Gamer

### Étape 1 : Cloner le Répertoire & Vérifier la Branche
Dans votre terminal (PowerShell, Git Bash ou WSL sous Windows ; Terminal sous Linux/Mac) :
```bash
git clone https://github.com/Justinbdna/bourbon-ia.git
cd bourbon-ia
git checkout main
# (ou git checkout feature/legistique-an-senat)
git pull origin main
```

---

### Étape 2 : Configuration du Backend Python (FastAPI)
1. **Créer et activer l'environnement virtuel :**
   - **Sous Windows (PowerShell) :**
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **Sous Linux / macOS / WSL :**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

2. **Installer les dépendances :**
   ```bash
   pip install --upgrade pip
   pip install fastapi uvicorn pydantic openai python-dotenv httpx pytest pytest-cov anyio
   ```
   *(Ou `pip install -r requirements.txt` complété)*

3. **Lancer le serveur API backend :**
   ```bash
   uvicorn api.index:app --reload --port 8000
   ```
   *Le backend est accessible sur `http://localhost:8000`. La documentation Swagger interactive est sur `http://localhost:8000/docs`.*

---

### Étape 3 : Configuration du Frontend React (Vite)
Dans un second terminal :
```bash
# Vérifier que Node.js v18+ est installé
node -v

# Installer les packages NPM
npm install

# Démarrer le serveur de développement Vite
npm run dev
```
*L'application s'ouvre sur `http://localhost:5173`.*

---

### Étape 4 : Configuration du LLM Local (Option Air-Gapped)
Pour exécuter l'IA 100 % en local sur votre carte graphique (Nvidia RTX / AMD) :
1. Installer [Ollama](https://ollama.com/) ou [LM Studio](https://lmstudio.ai/).
2. Télécharger le modèle recommandé :
   ```bash
   ollama run mistral
   # ou
   ollama run qwen2.5-coder:7b
   ```
3. Ollama expose son API par défaut sur `http://localhost:11434`.
4. Dans Bourbon.IA, cliquer sur le bouton **« Réglages IA »** (en haut à droite) et sélectionner **« Local (Ollama / LM Studio) »**.

---

### Étape 5 : Variables d'Environnement (Optionnel)
Copier le fichier `.env.example` en `.env` à la racine :
```bash
cp .env.example .env
```
Paramètres principaux :
- `VITE_API_URL=http://localhost:8000`
- `LLM_API_URL=http://127.0.0.1:11434/v1` (ou `http://127.0.0.1:1234/v1` pour LM Studio)
- `BOURBON_TEXTES_DISTANTS=1` (mettre `0` pour le mode totalement déconnecté).

---

## 🧪 4. Commandes de Test & Validation

Avant de pusher toute modification depuis votre PC gamer, lancez ces commandes pour garantir la stabilité :

```bash
# 1. Vérification du linter Frontend (0 warning, 0 error)
npx oxlint

# 2. Tests unitaires Frontend (Vitest - 35 tests)
npm test -- --run

# 3. Build de production Frontend (Vite)
npm run build

# 4. Tests unitaires Backend (Pytest - 101 tests)
pytest
```

---

## 📐 5. Règles & Conventions de Contribution

- **Nomenclature obligatoire des commits Git :**
  - `feat: [résumé court en français]` pour une nouvelle fonctionnalité.
  - `fix: [résumé court en français]` pour une correction de bug.
  - `style: [résumé court en français]` pour du formatage UI.
  - `refactor: [résumé court en français]` pour du remaniement de code.
- **Air-Gapped & Souveraineté :** Aucune clé d'API Cloud tierce obligatoire ; tout le traitement de texte confidentiel doit pouvoir tourner sur `localhost`.

---

## 🗺️ 6. Plan de Fichiers Essentiels

```
bourbon-ia/
├── api/
│   ├── index.py                    # Point d'entrée FastAPI & routes /api/v2/*
│   ├── deterministic_engine.py     # Règles de séance, Art. 98, Art. 45, tombants
│   ├── llm_semantic_engine.py      # Prompts IA en 3 points, RAG alinéa cible
│   ├── schemas.py                  # Modèles Pydantic EnrichedAmendment
│   ├── commissions_resolver.py     # Résolution des commissions et mots-clés
│   └── deputes_resolver.py         # Référentiel députés (AMO30 / Tricoteuses)
├── src/
│   ├── App.jsx                     # Composant racine, modales, arbitrage d'état
│   ├── components/
│   │   ├── AmendmentTable.jsx      # Tableau avec filtres, 1-clic arbitrage, pagination
│   │   ├── AmendmentDetail.jsx     # Volet de détail, word-diff, alertes séance
│   │   ├── GuidedDemo.jsx          # Démo guidée pas-à-pas avec lecteur MP3
│   │   └── amendment/
│   │       ├── AmendmentSearchBar.jsx # Multi-filtres (Article, Groupe, Thème, Auteur)
│   │       ├── BilanClassement.jsx    # Tuiles de synthèse cliquables
│   │       └── EUCompliancePanel.jsx  # Volet de surtransposition UE
│   └── utils/
│       ├── exportEloi.js           # Export JSON normalisé Éloi / LexImpact
│       ├── exportRtf.js            # Génération du préjaune parlementaire (.rtf)
│       └── tri.js                  # Tris parlementaires et naturels
└── tests/                          # 101 tests unitaires Pytest backend
```
