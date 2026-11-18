# Politique de Sécurité — Bourbon.IA

**Bourbon.IA** est conçu pour le traitement d'amendements parlementaires **avant leur publication en commission ou en séance publique**. La confidentialité des projets d'amendements, la souveraineté numérique et la défense contre les vulnérabilités applicatives sont des exigences non négociables.

---

## 1. Versions supportées

| Version | Statut de support |
| :--- | :--- |
| `v2.0.x` (`main`) | ✅ Supportée (correctifs de sécurité actifs) |
| `< v2.0.0` (prototypes Hackathon) | ❌ Non supportée |

---

## 2. Signaler une vulnérabilité

**Merci de ne pas ouvrir d'issue GitHub publique pour signaler une vulnérabilité de sécurité.**

Utilisez l'un des canaux privés suivants :
- **GitHub Security Advisories (recommandé)** : [Créer un avis de sécurité privé](https://github.com/Justinbdna/bourbon-ia/security/advisories/new)
- **Contenu souhaité** : description de la faille, composant ou endpoint concerné (`api/`, `api/mcp_server.py`, `src/`), scénario de reproduction et impact potentiel.

Nous nous engageons à :
- Accuser réception sous **48 heures ouvrées**.
- Fournir une analyse préliminaire sous **5 jours ouvrés**.
- Publier un correctif et créditer le chercheur (sauf souhait d'anonymat) avant toute divulgation publique.

---

## 3. Garanties Air-Gap & Confidentialité Avant Séance Publique

Pendant la fenêtre critique qui précède la publication officielle des amendements, aucune donnée textuelle confidentielle ne doit quitter le poste ou le réseau interne de l'Assemblée :

1. **Isolation réseau par défaut (`BOURBON_TEXTES_DISTANTS=0`)** :
   - Aucune requête HTTP sortante n'est déclenchée pour résoudre les textes de loi ou les participants lorsqu'une liasse est analysée en mode souverain (`api/textes_resolver.py`, `api/participants_resolver.py`, `api/import_dossier.py`, `api/index.py`).
   - Les référentiels de base (députés actifs, historique depuis 1997, commissions, base `data/bourbon_rag.db`) sont embarqués ou stockés localement.
2. **Inférence et embeddings 100 % locaux** :
   - Les moteurs IA compatibles OpenAI ciblent par défaut `localhost` / `127.0.0.1` (`Ollama` sur `:11434`, `LM Studio` sur `:1234`, ou conteneur local `http://ollama:11434`).
   - Le Vector Store SQLite (`api/services/rag_store.py`) fonctionne sans modèle distant grâce au repli lexical hybride BM25 / TF-IDF et impose un grounding strict (`"Information non disponible dans les sources"` sous le seuil).
3. **Consentement explicite en mode démo Cloud** :
   - Le mode de démonstration en ligne (Groq, réservé aux amendements **déjà publics**) n'est jamais activé silencieusement : l'interface exige la validation d'une modale de consentement explicite (`src/components/ConsentModal.jsx`) avant tout envoi vers un endpoint externe.
4. **Chiffrement local côté navigateur** :
   - La sauvegarde de session dans le navigateur utilise un chiffrement **AES-GCM** par blocs (`src/utils/crypto.js`).

---

## 4. Protections Applicatives & Anti-SSRF

### Protection Anti-SSRF (`api/llm_semantic_engine.py`)
La fonction `validate_endpoint_url()` contrôle tout endpoint personnalisé fourni à l'API ou au store d'embeddings :
- Rejet strict de tout schéma autre que `http` ou `https` (`file://`, `gopher://`, `ftp://`, etc.).
- En environnement Cloud (`VERCEL=1`), blocage systématique :
  - des hôtes de boucle locale (`localhost`, `127.0.0.1`, `0.0.0.0`, `::1`) et suffixes internes (`.local`, `.internal`, `.localhost`, `.lan`, `localtest.me`, `nip.io`, `sslip.io`) ;
  - des métadonnées Cloud (`169.254.169.254`, `metadata.google.internal`) ;
  - des plages IP privées RFC 1918 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), y compris après résolution DNS (`socket.getaddrinfo`).

### Hygiène des logs, bornage des charges & défense XSS
- **Masquage des secrets** : `sanitize_log_message()` neutralise automatiquement les clés API (`gsk_*`) et jetons `Bearer` avant journalisation ou remontée d'erreur.
- **Limitation de charge (anti-DoS / bombes zip)** :
  - Nombre d'amendements borné par `BOURBON_MAX_AMENDEMENTS` (`25000` par défaut dans `api/schemas.py`).
  - Décompression HTTP gzip bornée à `50 Mo` décompressés (`MAX_CORPS_DECOMPRESSE` dans `api/transport.py`).
- **Neutralisation XSS** : nettoyage HTML strict avant affichage React (`src/utils/sanitize.js`).
- **En-têtes HTTP de sécurité (`vercel.json`)** :
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`

---

## 5. Bonnes pratiques de déploiement souverain

- Laissez `BOURBON_TEXTES_DISTANTS=0` et `VITE_AI_PROVIDER_DEFAUT=local` en production interne.
- Ne commitez jamais de fichier `.env` ou de base `.db` contenant des amendements non publiés (`.gitignore` exclut déjà `.env*` et `*.db`).
- Préférez le déploiement conteneurisé via `docker/docker-compose.yml` sur un réseau isolé sans passerelle Internet sortante pour l'analyse de liasses confidentielles.
