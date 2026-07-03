# 🏗️ ARCHITECTURE ET CONTRAT DE DONNÉES (Hackathon Bourbon.IA)

## 1. CARTOGRAPHIE DU RÉSEAU (PORTS)

Suite à la perte temporaire du PC Gamer distant, l'architecture a été sécurisée 100% en local (Mac).

*   **🎨 FRONT-END (Justin / React Vite)**
    *   **Port cible** : `5173` (ou `3000` selon config locale).
    *   *Rôle* : Affiche l'UI, capture les fichiers JSON, et lance la requête HTTP. Plus aucun calcul lourd n'est fait côté client.
*   **⚙️ BACK-END (Yassine / FastAPI)**
    *   **Port cible** : `8000`.
    *   *Rôle* : Reçoit les données du Front, orchestre l'API, interroge le LLM et renvoie la donnée formatée.
*   **🧠 MOTEUR LLM (Mac Local / LM Studio)**
    *   **Port cible** : `1234`.
    *   **URL Base** : `http://127.0.0.1:1234/v1`
    *   *Rôle* : Inférence des modèles Mistral/Llama directement sur la machine locale.

---

## 2. CONTRAT DE DONNÉES (FRONT ↔ BACK)

Pour le MVP du hackathon, l'endpoint strict à respecter pour l'analyse des amendements est `/api/analyze`.

### Requête (Ce que le Front envoie au Back)
**POST** `http://127.0.0.1:8000/api/analyze`

```json
{
  "amendements": [
    {
      "id": "AMANR5L17PO59051B0149P0D1N000001",
      "texte": "À l'article 3, remplacer les mots « deux ans » par les mots « trois ans ».",
      "motif": "Allongement de prescription nécessaire."
    },
    {
      "id": "AMANR5L17PO59051B0149P0D1N000002",
      "texte": "Supprimer l'alinéa 4.",
      "motif": "Cet alinéa est anticonstitutionnel."
    }
  ],
  "model": "mac_mistral"
}
```

### Réponse (Ce que le Back renvoie au Front)
Le Backend boucle sur les amendements, les fait analyser au LLM de façon stricte, et renvoie ce tableau :

```json
[
  {
    "id": "AMANR5L17PO59051B0149P0D1N000001",
    "statut": "Incompatible",
    "justification": "Cet amendement modifie une durée de prescription déjà fixée par une directive européenne.",
    "alerte_couleur": "rouge"
  },
  {
    "id": "AMANR5L17PO59051B0149P0D1N000002",
    "statut": "Doublon",
    "justification": "Amendement identique déposé précédemment par le même groupe parlementaire.",
    "alerte_couleur": "orange"
  }
]
```

**Valeurs possibles pour `statut`** : `"Doublon"`, `"Identique"`, `"Incompatible"`, `"Nouveau"`, `"Erreur"`.
**Valeurs possibles pour `alerte_couleur`** : `"rouge"`, `"orange"`, `"vert"`.

---

> ⚠️ **Note pour Yassine** : 
> L'endpoint est déjà codé dans `main.py` et la logique de parsing Pydantic/LLM dans `scanner.py`. Si tu dois changer un détail dans la structure, pense à mettre à jour les classes `AnalyzeRequest` et `AnalyzeResult` !
