"""
api/llm_semantic_engine.py — Filtre sémantique LLM (Étape 3 du pipeline V2)
===========================================================================
Troisième et dernier étage du classement Bourbon.IA :

    1. PRÉ-TRI DÉTERMINISTE  (sortingEngine.js / sorting_engine.py)
       → tranche les Doublons et les Identiques stricts, SANS IA.
    2. ENRICHISSEMENT        (tricoteuses_client.py)
       → ajoute l'auteur (AMO 30) et le dossier législatif.
    3. FILTRE SÉMANTIQUE     ← CE MODULE
       → sur les seuls amendements encore marqués « NOUVEAU », détecte les
         SIMILITUDES de fond, c.-à-d. les DISCUSSIONS COMMUNES.

⚠️  RÈGLE D'OR ARCHITECTURALE
Le LLM n'a JAMAIS le droit de rejouer la hiérarchie légale de classement
(suppression d'article > rédaction globale > alinéa > mot à mot) : celle-ci
est déterministe et déjà appliquée en amont. Ici, le modèle répond à UNE
seule question sémantique : « cet amendement rejoint-il une discussion
commune existante, ou est-il isolé ? »

⚠️  MODULE ISOLÉ
Non branché à `api/index.py`. L'intégration fera l'objet d'une étape distincte.

Résilience : `evaluate_similitude()` ne lève JAMAIS d'exception. En cas
d'échec (timeout, serveur local éteint, JSON malformé, schéma invalide),
elle retourne le statut « NOUVEAU » avec `niveau_confiance = 0.0`, afin de
ne jamais bloquer le pipeline ni contaminer le classement.

Usage (auto-test hors-ligne, sans LLM requis) :
    python3 api/llm_semantic_engine.py
"""

from __future__ import annotations

import os
import ipaddress
import urllib.parse
import json
import logging
import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, ValidationError, model_validator

logger = logging.getLogger("bourbon.llm_semantic")


def sanitize_log_message(msg: str, key: Optional[str] = None) -> str:
    """Masque les clés API (Groq, OpenAI, etc.) dans les exceptions et logs."""
    if not msg:
        return ""
    clean = re.sub(r"gsk_[a-zA-Z0-9_-]{20,}", "[REDACTED_API_KEY]", str(msg))
    clean = re.sub(r"Bearer\s+[a-zA-Z0-9_\-\.]{15,}", "Bearer [REDACTED]", clean)
    if key and len(key) > 5 and key in clean:
        clean = clean.replace(key, "[REDACTED_API_KEY]")
    return clean


def validate_endpoint_url(endpoint: Optional[str]) -> str:
    """
    Validation anti-SSRF de l'URL du serveur LLM.
    En environnement Cloud / Vercel (VERCEL='1'), bloque impérativement :
      - Tout schéma non HTTP/HTTPS
      - Les hôtes locaux (localhost, 127.0.0.1, 0.0.0.0, [::1])
      - Les adresses de métadonnées cloud (169.254.169.254, metadata.google.internal)
      - Les plages d'adresses IP privées RFC 1918 (10.x, 172.16.x, 192.168.x)
    """
    if not endpoint or not str(endpoint).strip():
        return DEFAULT_ENDPOINT

    url = str(endpoint).strip()
    parsed = urllib.parse.urlsplit(url)

    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(f"Protocole non sécurisé ou invalide : '{parsed.scheme}'. Seuls HTTP et HTTPS sont autorisés.")

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError("URL d'endpoint invalide : nom d'hôte manquant.")

    is_cloud = os.environ.get("VERCEL") == "1"
    if is_cloud:
        if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"):
            raise ValueError("Accès aux hôtes locaux interdit en environnement Cloud (SSRF protection).")

        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or str(ip) == "169.254.169.254":
                raise ValueError("Accès aux réseaux privés et métadonnées interdit en environnement Cloud (SSRF protection).")
        except ValueError as ip_err:
            if "Accès" in str(ip_err):
                raise

    return url

# ──────────────────────────────────────────────────────────────────────────
# Garde-fous de contexte et compression drastique des tokens (Quota Groq 8K TPM)
# ──────────────────────────────────────────────────────────────────────────
# L'exposé sommaire est tronqué chirurgicalement à 180 caractères max (+ "...")
# pour garantir que la requête globale (system + user prompt) reste sous 400 tokens d'entrée.
MAX_EXPOSE_CHARS: int = 180
MAX_DISPOSITIF_CHARS: int = 600             # le dispositif est court par nature, nettoyé de tout HTML
MAX_CANDIDATS: int = 5                      # nombre de discussions candidates injectées au prompt (max 5)
MAX_CANDIDAT_EXTRAIT_CHARS: int = 250
MAX_DOSSIER_CHARS: int = 300

# Marqueur de coupe pour les textes tronqués
MARQUEUR_TRONCATURE: str = "..."

DEFAULT_ENDPOINT: str = "http://localhost:1234/v1"
DEFAULT_MODEL: str = "local-model"          # placeholder accepté par LM Studio
DEFAULT_TIMEOUT: float = 120.0
DEFAULT_MAX_TOKENS: int = 350               # bridage optimisé à 350 tokens (marge raisonnement + fermeture JSON)
LOCAL_MAX_TOKENS: int = 250                 # marge de sécurité à 250 tokens pour prévenir finish_reason='length'
DEFAULT_TEMPERATURE: float = 0.1            # tâche de jugement → quasi déterministe
GROQ_DEFAULT_MODEL: str = "openai/gpt-oss-20b"
GROQ_FALLBACK_MODELS: tuple[str, ...] = (
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
)


def _call_chat_completion_with_fallback(
    client: Any,
    *,
    is_groq: bool,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    stop: Optional[list[str]] = None,
) -> Any:
    """
    Exécute client.chat.completions.create avec repli automatique de modèle sur Groq
    si le modèle demandé renvoie 404 model_not_found / décommissionné ou 429 rate_limit_exceeded.
    Donne la priorité aux modèles légers à quota TPM élevé (llama-3.1-8b-instant, openai/gpt-oss-20b).
    """
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if stop:
        kwargs["stop"] = stop

    try:
        return client.chat.completions.create(**kwargs)
    except Exception as first_exc:
        exc_msg = str(first_exc).lower()
        exc_type = type(first_exc).__name__
        is_recoverable_groq_err = (
            "notfounderror" in exc_type.lower()
            or "ratelimiterror" in exc_type.lower()
            or "model_not_found" in exc_msg
            or "rate_limit" in exc_msg
            or "429" in exc_msg
            or "decommissioned" in exc_msg
            or "does not exist" in exc_msg
            or "do not have access" in exc_msg
        )
        if not is_groq or not is_recoverable_groq_err:
            raise
        for fallback_model in GROQ_FALLBACK_MODELS:
            if fallback_model == model:
                continue
            try:
                kwargs["model"] = fallback_model
                return client.chat.completions.create(**kwargs)
            except Exception as fb_exc:
                fb_msg = str(fb_exc).lower()
                fb_type = type(fb_exc).__name__.lower()
                if (
                    "model_not_found" in fb_msg
                    or "does not exist" in fb_msg
                    or "do not have access" in fb_msg
                    or "ratelimiterror" in fb_type
                    or "rate_limit" in fb_msg
                    or "429" in fb_msg
                ):
                    continue
                raise
        raise first_exc


def _is_local_endpoint(endpoint: Optional[str]) -> bool:
    """Détecte si l'endpoint vise un serveur local (Ollama / LM Studio sur localhost / 127.0.0.1)."""
    if not endpoint:
        return True
    lower = str(endpoint).lower()
    return any(h in lower for h in ("localhost", "127.0.0.1", "0.0.0.0", "[::1]", "::1"))


# ══════════════════════════════════════════════════════════════════════════
# 1. SCHÉMA PYDANTIC — Chain of Thought
# ══════════════════════════════════════════════════════════════════════════
# Statuts qui DÉSIGNENT une discussion existante : sans identifiant de cible,
# le verdict est inexploitable pour construire le dérouleur.
STATUTS_AVEC_CIBLE: frozenset[str] = frozenset(
    {"Discussion commune", "Identique", "Similaire"}
)
# Statuts qui affirment au contraire l'ISOLEMENT : toute cible est contradictoire.
STATUTS_SANS_CIBLE: frozenset[str] = frozenset({"Isolé", "NOUVEAU"})
class LLMClassificationResponse(BaseModel):
    """
    Réponse structurée attendue du LLM, concise et sans gaspillage de tokens.
    Accepte le format minifié {"statut", "confiance", "justification", "id_discussion_cible"}
    tout en préservant la compatibilité avec {"analyse_intention", "analyse_politique", "niveau_confiance"}.
    """

    statut: Literal["Identique", "Similaire", "Discussion commune", "Isolé", "NOUVEAU"] = Field(
        ...,
        description="Verdict final de l'analyse sémantique.",
    )
    confiance: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confiance du modèle (0.0 à 1.0).",
    )
    niveau_confiance: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Confiance du modèle, de 0.0 à 1.0. Par convention, 0.0 signale un repli technique.",
    )
    justification: Optional[str] = Field(
        default=None,
        description="Explication concise en 1 phrase maximum.",
    )
    analyse_intention: str = Field(
        default="",
        description="Ce que l'auteur cherche concrètement à modifier dans le texte.",
    )
    analyse_politique: str = Field(
        default="",
        description="Lecture politique de l'amendement.",
    )
    id_discussion_cible: Optional[str] = Field(
        default=None,
        description="Identifiant de la discussion rejointe. OBLIGATOIRE si "
                    "statut = DISCUSSION_COMMUNE, et doit provenir des candidats "
                    "fournis (jamais inventé). None si statut = NOUVEAU.",
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normaliser confiance / niveau_confiance
            conf = data.get("confiance")
            niv = data.get("niveau_confiance")
            if conf is not None and niv is None:
                data["niveau_confiance"] = float(conf)
            elif niv is not None and conf is None:
                data["confiance"] = float(niv)

            # Normaliser justification / analyse_intention / analyse_politique
            just = data.get("justification")
            inten = data.get("analyse_intention")
            pol = data.get("analyse_politique")
            if just and not inten:
                data["analyse_intention"] = str(just)
            if just and not pol:
                data["analyse_politique"] = str(just)
            if inten and not just:
                data["justification"] = str(inten)
        return data

    @model_validator(mode="after")
    def _coherence_statut_cible(self) -> "LLMClassificationResponse":
        """
        Refuse les réponses incohérentes.
        """
        if self.statut in STATUTS_AVEC_CIBLE and not self.id_discussion_cible:
            # evaluate_similitude se charge d'assigner le premier candidat valide
            pass
        if self.statut in STATUTS_SANS_CIBLE and self.id_discussion_cible:
            self.id_discussion_cible = None
        return self


# ══════════════════════════════════════════════════════════════════════════
# 2. TRONCATURE INTELLIGENTE & CHIRURGICALE (< 180 CARACTÈRES)
# ══════════════════════════════════════════════════════════════════════════
def _tronquer_expose_180(texte: Optional[str]) -> str:
    """Conserve strictement les 180 premiers caractères de l'exposé sommaire suivis de '...'."""
    if not texte:
        return ""
    propre = re.sub(r"<[^>]+>", " ", str(texte))
    propre = re.sub(r"\s+", " ", propre).strip()
    if not propre:
        return ""
    if len(propre) <= MAX_EXPOSE_CHARS:
        return propre
    return propre[:MAX_EXPOSE_CHARS].rstrip() + "..."


def _nettoyer_dispositif(texte: Optional[str], limite: int = MAX_DISPOSITIF_CHARS) -> str:
    """Nettoie le HTML et les espaces parasites du dispositif."""
    if not texte:
        return ""
    propre = re.sub(r"<[^>]+>", " ", str(texte))
    propre = re.sub(r"\s+", " ", propre).strip()
    if len(propre) <= limite:
        return propre
    return propre[:limite].rstrip() + "..."


def _tronquer_intelligemment(texte: Optional[str], limite: int) -> str:
    """
    Tronque sans couper au milieu d'un mot, en privilégiant une frontière
    naturelle (fin de phrase, sinon fin de mot), et signale explicitement la
    coupe au modèle pour qu'il ne prenne pas le texte pour complet.

    Nettoie au passage les balises HTML et les espaces parasites : les JSON
    de l'Assemblée contiennent du `<p>`, du `<br/>` et des retours multiples
    qui gaspillent des tokens sans apporter de sens.
    """
    if not texte:
        return ""

    propre = re.sub(r"<[^>]+>", " ", str(texte))       # balises HTML
    propre = re.sub(r"[ \t]+", " ", propre)            # espaces multiples
    propre = re.sub(r"\n{3,}", "\n\n", propre).strip() # sauts de ligne excessifs

    if len(propre) <= limite:
        return propre

    # On RÉSERVE la place du marqueur pour que la chaîne renvoyée respecte
    # strictement `limite` — sinon la borne serait dépassée de la longueur du
    # marqueur, ce qui viderait de son sens le garde-fou de contexte.
    budget = max(1, limite - len(MARQUEUR_TRONCATURE))
    fenetre = propre[:budget]

    # 1er choix : dernière fin de phrase dans le dernier tiers de la fenêtre.
    frontiere = max(fenetre.rfind(". "), fenetre.rfind(".\n"), fenetre.rfind(" ; "))
    if frontiere < budget * 0.6:
        # 2e choix : dernier espace (on ne coupe jamais un mot en deux).
        frontiere = fenetre.rfind(" ")
    if frontiere <= 0:
        frontiere = budget

    return fenetre[:frontiere].rstrip(" ,;:") + MARQUEUR_TRONCATURE


# ══════════════════════════════════════════════════════════════════════════
# 3. SYSTEM PROMPT ULTRA-COMPACT (< 40 TOKENS)
# ══════════════════════════════════════════════════════════════════════════
SYSTEM_PROMPT: str = (
    "Tu es un juriste parlementaire. Détermine si deux amendements doivent être en 'Discussion commune', "
    "'Identique' ou 'Isolé'. Commence DIRECTEMENT ta réponse par '{'. N'émets aucun préambule, bloc de pensée ni explication hors du JSON. "
    "Réponds STRICTEMENT en JSON minifié : "
    '{"statut":"...","confiance":0.9,"justification":"1 phrase max"}'
)

LOCAL_SYSTEM_PROMPT: str = (
    "Administrateur légistique de séance. Compare l'amendement candidat aux amendements déposés sur le même article.\n"
    "Réponds EXCLUSIVEMENT par un unique objet JSON fermé sur une ligne.\n"
    'Schéma strict : {"statut":"Isolé"|"Identique"|"Discussion commune","confiance":0.85,"cible":null|"NUMERO","justification":"1 phrase concise"}\n'
    "Interdiction absolue de générer du texte hors du JSON."
)

LOCAL_ONE_SHOT_MESSAGES: list[dict[str, str]] = [
    {
        "role": "user",
        "content": "Amendement A (Article 3) : Supprimer l'alinéa 1.",
    },
    {
        "role": "assistant",
        "content": '{"statut":"Isolé","confiance":0.95,"cible":null,"justification":"Suppression sans autre amendement concurrent sur cet alinéa."}',
    },
]

LOCAL_STOP_SEQUENCES: list[str] = ["\n\n", "}\n", "\n{", "```"]


# ══════════════════════════════════════════════════════════════════════════
# 4. CONSTRUCTION DU PROMPT UTILISATEUR
# ══════════════════════════════════════════════════════════════════════════
def _sget(source: Any, *cles: str, defaut: Any = None) -> Any:
    """Lecture imbriquée tolérante — aucun KeyError possible."""
    courant = source
    for cle in cles:
        if not isinstance(courant, dict):
            return defaut
        courant = courant.get(cle)
        if courant is None:
            return defaut
    return courant


def _resumer_candidat(candidat: dict[str, Any], rang: int) -> dict[str, Any]:
    """
    Réduit un candidat à l'article court, au dispositif nettoyé et à l'exposé sommaire (180 car. max).
    Supprime toute métadonnée superflue (ID long, groupe politique, auteur, date).
    """
    amd = candidat.get("amendement", candidat)

    identifiant = (
        candidat.get("id_discussion")
        or candidat.get("groupe_id")
        or amd.get("idDiscussionIdentique")
        or amd.get("uid")
        or f"CAND-{rang}"
    )

    article = (
        amd.get("divisionArticleDesignationCourte")
        or amd.get("divisionArticleDesignation")
        or amd.get("article_vise")
        or "Article"
    )

    disp = _nettoyer_dispositif(
        amd.get("dispositif") or amd.get("dispositif_raw") or amd.get("texte") or "",
        MAX_CANDIDAT_EXTRAIT_CHARS,
    )
    expose = _tronquer_expose_180(amd.get("exposeSommaire") or amd.get("expose_sommaire"))

    res: dict[str, str] = {
        "id_discussion": str(identifiant),
        "article": str(article),
        "dispositif": disp,
    }
    if expose:
        res["expose"] = expose
    return res


def generate_classification_prompt(
    amendement_enrichi: dict[str, Any],
    contexte: Any = None,
    texte_loi_reference: Optional[str] = None,
) -> str:
    """
    Construit le prompt utilisateur, sous contrainte stricte de tokens.

    Args:
        amendement_enrichi  : structure produite par le pipeline d'enrichissement
                              (sections `amendement`, `auteur`, `dossier`).
        contexte            : discussions candidates. Accepte une liste de dicts,
                              ou un dict contenant `candidats` / `discussions`.
        texte_loi_reference : texte initial de l'article de loi visé (si disponible).

    Returns:
        Le prompt utilisateur prêt à être envoyé au modèle.
    """
    amd = amendement_enrichi.get("amendement", amendement_enrichi)
    texte_ref = texte_loi_reference or amendement_enrichi.get("texte_loi_reference")

    # ── Normalisation des candidats (max 5) ──
    if isinstance(contexte, dict):
        brut = contexte.get("candidats") or contexte.get("discussions") or []
    elif isinstance(contexte, list):
        brut = contexte
    else:
        brut = []

    candidats = [
        _resumer_candidat(c, i + 1)
        for i, c in enumerate(brut[:MAX_CANDIDATS])
        if isinstance(c, dict)
    ]

    # Article court et dispositif nettoyé
    article_court = (
        amd.get("divisionArticleDesignationCourte")
        or amd.get("divisionArticleDesignation")
        or amd.get("article_vise")
        or "Article"
    )
    dispositif = _nettoyer_dispositif(amd.get("dispositif") or amd.get("dispositif_raw") or amd.get("texte") or "")
    expose = _tronquer_expose_180(amd.get("exposeSommaire") or amd.get("expose_sommaire"))

    lignes: list[str] = [
        f"Amendement à classer ({article_court}) :",
        f"Dispositif : {dispositif or 'Non renseigné'}",
    ]
    if expose:
        lignes.append(f"Exposé : {expose}")

    # ── Injection du texte de loi de référence (Chantier 2) ──
    if texte_ref:
        article_nom = amd.get("divisionArticleDesignation") or "Article"
        lignes.extend([
            "",
            f'<TEXTE_LOI_INITIAL article="{article_nom}">',
            _nettoyer_dispositif(str(texte_ref).strip(), 300),
            "</TEXTE_LOI_INITIAL>",
            "",
            "Consigne stricte : Tu dois analyser l'impact des amendements en concurrence PAR RAPPORT au texte de loi initial ci-dessus. "
            "Deux amendements modifiant la même phrase du texte initial ou ayant des effets incompatibles doivent être classés en 'Discussion commune'.",
        ])

    if candidats:
        lignes.append("\nCandidats concurrents :")
        for c in candidats:
            ligne_c = f"- [{c['id_discussion']}] {c['article']} : {c['dispositif']}"
            if c.get("expose"):
                ligne_c += f" | Exposé : {c['expose']}"
            lignes.append(ligne_c)
    else:
        lignes.append("\nAucun candidat concurrent. Statut : Isolé.")

    lignes.append("Commence DIRECTEMENT ta réponse par '{'. N'émets aucun préambule, bloc de pensée ni explication hors du JSON.")

    return "\n".join(lignes)


# ══════════════════════════════════════════════════════════════════════════
# 5. EXTRACTION ET RÉPARATION JSON ROBUSTE (modèles bavards / reasoning)
# ══════════════════════════════════════════════════════════════════════════
def _reparer_json(texte: str) -> str:
    """
    Répare un JSON tronqué ou malformé généré par un LLM :
    - Élimine les blocs de réflexion <think>...</think> résiduels
    - Ferme les chaînes de caractères orphelines (guillemets non fermés)
    - Supprime les virgules traînantes avant les fermetures
    - Ferme les crochets et accolades non équilibrés
    """
    if not texte:
        return ""

    s = re.sub(r"<think>.*?</think>", " ", texte, flags=re.DOTALL | re.IGNORECASE)
    s = re.sub(r"<think>.*$", " ", s, flags=re.DOTALL | re.IGNORECASE)
    s = re.sub(r"```[a-zA-Z]*", " ", s).replace("```", " ").strip()

    premier_idx = s.find("{")
    if premier_idx == -1:
        return s
    s = s[premier_idx:]

    try:
        json.loads(s)
        return s
    except Exception:
        pass

    s = re.sub(r":\s*$", ': ""', s)

    dans_chaine = False
    echappe = False
    accolades_ouvertes = 0
    crochets_ouverts = 0

    for car in s:
        if dans_chaine:
            if echappe:
                echappe = False
            elif car == "\\":
                echappe = True
            elif car == '"':
                dans_chaine = False
            continue
        if car == '"':
            dans_chaine = True
        elif car == "{":
            accolades_ouvertes += 1
        elif car == "}":
            if accolades_ouvertes > 0:
                accolades_ouvertes -= 1
        elif car == "[":
            crochets_ouverts += 1
        elif car == "]":
            if crochets_ouverts > 0:
                crochets_ouverts -= 1

    repare = s
    if dans_chaine:
        repare += '"'
    if crochets_ouverts > 0:
        repare += "]" * crochets_ouverts
    if accolades_ouvertes > 0:
        repare += "}" * accolades_ouvertes

    repare = re.sub(r",\s*([\}\]])", r"\1", repare)

    try:
        json.loads(repare)
        return repare
    except Exception:
        dernier_delim = max(repare.rfind(","), repare.rfind("{"))
        if dernier_delim > 0:
            tronque = repare[:dernier_delim].rstrip()
            open_braces = max(0, tronque.count("{") - tronque.count("}"))
            if open_braces > 0:
                tronque += "}" * open_braces
            try:
                json.loads(tronque)
                return tronque
            except Exception:
                pass
        return repare


def _extraire_json(contenu: str) -> str:
    """
    Isole l'objet JSON d'une réponse de modèle, y compris quand celui-ci
    « pense à voix haute » ou produit du bavardage multi-lignes.

    Stratégie : on retire les blocs `<think>` et les clôtures Markdown,
    puis on extrait en priorité le PREMIER bloc JSON complet et équilibré
    pour couper court à toute tentative d'hallucination ou répétition de blocs.
    """
    if not contenu:
        raise ValueError("Réponse vide du modèle.")

    texte = re.sub(r"<think>.*?</think>", " ", contenu, flags=re.DOTALL | re.IGNORECASE)
    texte = re.sub(r"<think>.*$", " ", texte, flags=re.DOTALL | re.IGNORECASE)  # bloc non fermé
    texte = re.sub(r"```[a-zA-Z]*", " ", texte).replace("```", " ").strip()

    # Détection rapide d'un premier bloc JSON compact sans imbrication
    match_direct = re.search(r"\{[^{}]*\}", texte)
    if match_direct:
        candidat = match_direct.group(0)
        try:
            json.loads(candidat)
            return candidat
        except Exception:
            pass

    objets: list[str] = []
    profondeur = 0
    debut: Optional[int] = None
    dans_chaine = False
    echappe = False

    for i, car in enumerate(texte):
        if dans_chaine:
            if echappe:
                echappe = False
            elif car == "\\":
                echappe = True
            elif car == '"':
                dans_chaine = False
            continue
        if car == '"':
            dans_chaine = True
        elif car == "{":
            if profondeur == 0:
                debut = i
            profondeur += 1
        elif car == "}" and profondeur > 0:
            profondeur -= 1
            if profondeur == 0 and debut is not None:
                objets.append(texte[debut:i + 1])
                debut = None

    if objets:
        # En priorité le premier objet JSON complet valide
        for obj in objets:
            try:
                json.loads(obj)
                return obj
            except Exception:
                continue
        return objets[0]

    # Si aucun objet équilibré strict n'a été trouvé, tenter la réparation résiliente
    premier_idx = texte.find("{")
    if premier_idx != -1:
        repare = _reparer_json(texte[premier_idx:])
        if repare:
            return repare

    raise ValueError("Aucun objet JSON équilibré trouvé dans la réponse.")


def _repli_nouveau(motif: str) -> LLMClassificationResponse:
    """
    Réponse de repli : le pipeline continue coûte que coûte.

    Convention : `niveau_confiance = 0.0` signale sans ambiguïté qu'aucun
    verdict n'a été rendu par le modèle. Un consommateur en aval peut ainsi
    distinguer « le LLM a jugé isolé » (confiance > 0) de « le LLM n'a pas
    répondu » (confiance == 0) et, par exemple, marquer la ligne pour revue
    humaine dans le dashboard.
    """
    logger.warning(f"⚠️  Repli sémantique → NOUVEAU. Motif : {motif}")
    intention = motif if motif.startswith("⚠️") else f"Analyse sémantique indisponible ({motif})."
    return LLMClassificationResponse(
        analyse_intention=intention,
        analyse_politique="Aucune analyse politique produite : repli technique. "
                          "Classement laissé au moteur déterministe.",
        justification=intention,
        statut="NOUVEAU",
        id_discussion_cible=None,
        niveau_confiance=0.0,
        confiance=0.0,
    )


# ══════════════════════════════════════════════════════════════════════════
# 6. ORCHESTRATEUR
# ══════════════════════════════════════════════════════════════════════════
def evaluate_similitude(
    amendement_enrichi: dict[str, Any],
    contexte: Any = None,
    llm_endpoint: Optional[str] = None,
    *,
    provider: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    api_key: str = "local-key",
    key_source: str = "payload",
    timeout: float = DEFAULT_TIMEOUT,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    stop: Optional[list[str]] = None,
    texte_loi_reference: Optional[str] = None,
) -> LLMClassificationResponse:
    """
    Interroge le LLM local et renvoie une classification sémantique validée.

    NE LÈVE JAMAIS D'EXCEPTION : tout échec (serveur éteint, timeout, JSON
    malformé, schéma incohérent) est converti en repli « NOUVEAU » avec
    `niveau_confiance = 0.0`.
    """
    prompt_utilisateur = generate_classification_prompt(
        amendement_enrichi, contexte, texte_loi_reference=texte_loi_reference
    )

    try:
        # Import paresseux : cohérent avec api/index.py, évite de faire échouer
        # le build serverless si la dépendance manque au moment du bundling.
        from openai import OpenAI

        effective_endpoint = validate_endpoint_url(llm_endpoint)
        is_groq = "api.groq.com" in effective_endpoint or provider in ("groq", "groq_auto")
        is_local = _is_local_endpoint(effective_endpoint) or provider in ("local", "lmstudio")

        if is_local:
            effective_max_tokens = min(max_tokens or 250, 250)
            messages = [
                {"role": "system", "content": LOCAL_SYSTEM_PROMPT},
                *LOCAL_ONE_SHOT_MESSAGES,
                {"role": "user", "content": prompt_utilisateur},
            ]
            effective_stop = stop if stop is not None else LOCAL_STOP_SEQUENCES
        else:
            effective_max_tokens = min(max_tokens or 350, 350)
            if is_groq:
                if not model or model in ("local-model", "default", "llama3-8b-8192", "llama3-70b-8192", "llama-3.3-70b-versatile", ""):
                    model = GROQ_DEFAULT_MODEL
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt_utilisateur},
            ]
            effective_stop = stop

        clean_key = str(api_key).strip() if api_key else ""
        default_headers = None
        if is_groq or clean_key:
            default_headers = {
                "Authorization": f"Bearer {clean_key}",
                "Content-Type": "application/json",
            }

        client = OpenAI(
            base_url=effective_endpoint,
            api_key=clean_key or "local-key",
            timeout=timeout,
            default_headers=default_headers,
        )
        reponse = _call_chat_completion_with_fallback(
            client,
            is_groq=is_groq,
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=effective_max_tokens,
            stop=effective_stop,
        )
        contenu = (reponse.choices[0].message.content or "").strip()

    except ImportError:
        return _repli_nouveau("bibliothèque openai indisponible")
    except Exception as exc:
        exc_str = sanitize_log_message(str(exc), api_key)
        exc_name = type(exc).__name__
        if (
            "AuthenticationError" in exc_name
            or "PermissionDeniedError" in exc_name
            or "401" in exc_str
            or "403" in exc_str
            or "Invalid API Key" in exc_str
            or "invalid_api_key" in exc_str
        ):
            auth_msg = (
                "Clé API Groq personnelle invalide ou expirée"
                if key_source == "payload"
                else "Clé API Groq Vercel du projet invalide"
            )
            return _repli_nouveau(auth_msg)
        # Couvre APITimeoutError, APIConnectionError (LM Studio éteint, CORS,
        # pare-feu), erreurs HTTP, réponses inattendues du serveur local.
        return _repli_nouveau(f"{exc_name}: {exc_str[:180]}")

    # ── Parsing (2 tentatives résilientes) ──
    donnees = None
    if not contenu or not contenu.strip():
        return _repli_nouveau("Réponse vide du modèle.")

    try:
        # Tentative 1 : extraction équilibrée
        brut = _extraire_json(contenu)
        donnees = json.loads(brut)
    except Exception as exc1:
        # Tentative 2 : réparation résiliente d'urgence
        try:
            premier_acc = contenu.find("{")
            if premier_acc != -1:
                repare = _reparer_json(contenu[premier_acc:])
                donnees = json.loads(repare)
            else:
                raise ValueError("Aucun objet JSON équilibré trouvé dans la réponse.")
        except Exception as exc2:
            logger.debug(f"Réponse brute non parsable après 2 tentatives : {contenu[:400]}")
            return _repli_nouveau(f"JSON illisible ({exc1})")

    # ── Validation de schéma ──
    try:
        resultat = LLMClassificationResponse(**donnees)
    except ValidationError as exc:
        premiere = exc.errors()[0] if exc.errors() else {}
        champ = ".".join(str(p) for p in premiere.get("loc", ())) or "?"
        return _repli_nouveau(f"schéma invalide sur '{champ}': {premiere.get('msg', exc)}")
    except TypeError as exc:
        return _repli_nouveau(f"structure inattendue ({exc})")

    # ── Garde-fou anti-hallucination : l'identifiant doit exister ──
    # (tous les statuts qui désignent une cible : « Discussion commune »,
    # « Identique », « Similaire » — libellés exacts du schéma ci-dessus)
    if resultat.statut in STATUTS_AVEC_CIBLE:
        ids_valides = {
            _resumer_candidat(c, i + 1)["id_discussion"]
            for i, c in enumerate(
                (contexte if isinstance(contexte, list) else
                 (contexte or {}).get("candidats", []) if isinstance(contexte, dict) else [])
            )
            if isinstance(c, dict)
        }
        if not resultat.id_discussion_cible:
            if ids_valides:
                resultat.id_discussion_cible = next(iter(ids_valides))
            else:
                return _repli_nouveau("aucun candidat disponible pour ce statut avec cible")
        elif resultat.id_discussion_cible not in ids_valides:
            return _repli_nouveau(
                f"identifiant halluciné « {resultat.id_discussion_cible} » "
                f"(absent des candidats fournis)"
            )

    logger.info(
        f"✅ Verdict sémantique : {resultat.statut} "
        f"(cible={resultat.id_discussion_cible}, confiance={resultat.niveau_confiance:.2f})"
    )
    return resultat


# ══════════════════════════════════════════════════════════════════════════
# 6 bis. RÉSUMÉ D'UN AMENDEMENT (à la demande, depuis la fiche de détail)
# ══════════════════════════════════════════════════════════════════════════
MAX_RESUME_CHARS: int = 600
MAX_TEXTE_LOI_CHARS: int = 1500

RESUME_SYSTEM_PROMPT: str = """Tu es administrateur à l'Assemblée nationale française. Tu résumes des amendements pour tes collègues, de façon strictement NEUTRE : tu décris ce que l'amendement change, jamais s'il est bon ou mauvais, et tu ne reprends pas l'argumentaire politique de l'auteur.

Règles :
- 2 phrases au maximum, en français, sans liste ni titre ni guillemets autour de la réponse.
- Phrase 1 : l'effet concret sur le texte (ce qui est supprimé, ajouté ou modifié, et où).
- Phrase 2 (facultative) : l'objectif déclaré par l'auteur, introduit par « L'auteur vise à ».
- N'invente rien : si le dispositif est vide ou illisible, réponds exactement « Dispositif non renseigné. »"""


def resumer_amendement(
    dispositif: Optional[str],
    expose_sommaire: Optional[str] = None,
    article: Optional[str] = None,
    texte_loi_reference: Optional[str] = None,
    llm_endpoint: Optional[str] = None,
    *,
    model: str = DEFAULT_MODEL,
    api_key: str = "local-key",
    key_source: str = "payload",
    timeout: float = 60.0,
) -> str:
    """
    Résume un amendement en 1 à 2 phrases neutres.

    Lève RuntimeError avec un message lisible (clé masquée) en cas d'échec :
    contrairement au classement, il n'y a pas de repli déterministe utile.
    """
    dispositif_propre = _tronquer_intelligemment(dispositif, MAX_DISPOSITIF_CHARS)
    if not dispositif_propre:
        return "Dispositif non renseigné."

    parties = [f"Article visé : {article or 'non précisé'}", f"Dispositif :\n{dispositif_propre}"]
    if texte_loi_reference:
        parties.append(
            "Texte de loi visé (pour situer la modification) :\n"
            + _tronquer_intelligemment(texte_loi_reference, MAX_TEXTE_LOI_CHARS)
        )
    if expose_sommaire:
        parties.append("Exposé sommaire de l'auteur :\n" + _tronquer_intelligemment(expose_sommaire, MAX_EXPOSE_CHARS))

    try:
        from openai import OpenAI

        effective_endpoint = validate_endpoint_url(llm_endpoint)
        is_groq = "api.groq.com" in effective_endpoint

        if is_groq:
            if not model or model in ("local-model", "default", "llama3-8b-8192", "llama3-70b-8192", "llama-3.3-70b-versatile", ""):
                model = GROQ_DEFAULT_MODEL

        clean_key = str(api_key).strip() if api_key else ""
        default_headers = None
        if is_groq or clean_key:
            default_headers = {
                "Authorization": f"Bearer {clean_key}",
                "Content-Type": "application/json",
            }

        client = OpenAI(
            base_url=effective_endpoint,
            api_key=clean_key or "local-key",
            timeout=timeout,
            default_headers=default_headers,
        )
        reponse = _call_chat_completion_with_fallback(
            client,
            is_groq=is_groq,
            model=model,
            messages=[
                {"role": "system", "content": RESUME_SYSTEM_PROMPT},
                {"role": "user", "content": "\n\n".join(parties)},
            ],
            temperature=0.1,
            max_tokens=200,
        )
        resume = (reponse.choices[0].message.content or "").strip().strip('"«» ')
    except ImportError as exc:
        raise RuntimeError("Bibliothèque openai indisponible sur le serveur.") from exc
    except ValueError as exc:
        # Adresse refusée par validate_endpoint_url (ex. « IA locale » demandée
        # depuis la démo en ligne) : message explicite pour l'utilisateur.
        raise RuntimeError(sanitize_log_message(str(exc), api_key)) from None
    except Exception as exc:
        exc_str = sanitize_log_message(str(exc), api_key)
        exc_name = type(exc).__name__
        if (
            "AuthenticationError" in exc_name
            or "PermissionDeniedError" in exc_name
            or "401" in exc_str
            or "403" in exc_str
            or "invalid_api_key" in exc_str
            or "Invalid API Key" in exc_str
        ):
            auth_msg = (
                "Clé API Groq personnelle invalide ou expirée"
                if key_source == "payload"
                else "Clé API Groq Vercel du projet invalide"
            )
            raise RuntimeError(auth_msg) from None
        if "Connection" in exc_name:
            raise RuntimeError(
                "Serveur d'IA injoignable : vérifiez que LM Studio / Ollama est démarré, "
                "ou choisissez « Groq (Démo) » dans les Réglages IA."
            ) from None
        raise RuntimeError(f"IA indisponible ({exc_name}).") from None

    if not resume:
        raise RuntimeError("Réponse vide de l'IA.")
    return resume[:MAX_RESUME_CHARS]


# ══════════════════════════════════════════════════════════════════════════
# 7. AUTO-TEST HORS-LIGNE (aucun LLM requis)
# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    exemple = {
        "amendement": {
            "uid": "AMANR5L17TEST0001",
            "numeroLong": "CL19",
            "dispositif": "Supprimer cet article.",
            "exposeSommaire": ("Argumentaire très long. " * 400),  # ~9 000 caractères
            "divisionArticleDesignation": "ARTICLE 5",
            "estIdentique": True,
        },
        "auteur": {
            "uid": "PA841701", "nom": "Balage El Mariky", "prenom": "Léa",
            "trigramme": "EcoS",
            "groupePolitiqueRef": {"uid": "PO845439", "libelle": "Écologiste et Social"},
        },
        "dossier": {"uid": "DLR5L17N54094", "titre": "Projet de loi test",
                    "procedure": "Projet de loi ordinaire"},
    }
    candidats = [{
        "id_discussion": "DISC-ART5-SUPPR",
        "amendement": {"divisionArticleDesignation": "ARTICLE 5",
                       "dispositif": "Supprimer cet article."},
        "auteur": {"groupePolitiqueRef": {"libelle": "La France insoumise"}},
    }]

    print("═" * 66)
    print("  AUTO-TEST · Moteur sémantique LLM (hors-ligne)")
    print("═" * 66)

    # 1 · Troncature chirurgicale
    prompt = generate_classification_prompt(exemple, candidats)
    expose_lignes = [l for l in prompt.split("\n") if l.startswith("Exposé :")]
    expose_taille = len(expose_lignes[0]) if expose_lignes else 0
    print(f"1. Troncature chirurgicale : {len(exemple['amendement']['exposeSommaire'])} car. "
          f"→ {expose_taille} car. "
          f"| points de suspension présents : {'...' in prompt}")
    print(f"   Prompt total (< 400 car)    : {len(prompt)} caractères")

    # 2 · Extraction JSON malgré un raisonnement bavard contenant des accolades
    bavard = (
        "<think>Je dois répondre au format {\"statut\": ...} donc je réfléchis…</think>\n"
        "Voici mon analyse : le schéma attendu est {exemple: {imbriqué: 1}}.\n"
        "```json\n"
        '{"analyse_intention":"Suppression de l\'article 5.",'
        '"analyse_politique":"Convergence d\'opposition.",'
        '"statut":"Discussion commune","id_discussion_cible":"DISC-ART5-SUPPR",'
        '"niveau_confiance":0.95}\n'
        "```"
    )
    valide = LLMClassificationResponse(**json.loads(_extraire_json(bavard)))
    print(f"2. Extraction CoT      : ✅ statut={valide.statut} "
          f"cible={valide.id_discussion_cible} confiance={valide.niveau_confiance}")

    # 3 · Rejet d'une réponse incohérente
    try:
        LLMClassificationResponse(analyse_intention="a", analyse_politique="b",
                                  statut="DISCUSSION_COMMUNE",
                                  id_discussion_cible=None, niveau_confiance=0.9)
        print("3. Cohérence schéma    : ❌ incohérence NON détectée")
    except ValidationError:
        print("3. Cohérence schéma    : ✅ DISCUSSION_COMMUNE sans cible rejetée")

    # 4 · Fallback quand le serveur local est injoignable
    repli = evaluate_similitude(exemple, candidats,
                                llm_endpoint="http://127.0.0.1:9/v1", timeout=3)
    print(f"4. Fallback réseau     : {'✅' if repli.statut == 'NOUVEAU' and repli.niveau_confiance == 0.0 else '❌'} "
          f"statut={repli.statut} confiance={repli.niveau_confiance}")

    # 5 · Absence de candidat → Isolé imposé par le prompt
    sans = generate_classification_prompt(exemple, [])
    print(f"5. Contexte vide       : {'✅' if 'Aucun candidat' in sans else '❌'} "
          "consigne Isolé injectée")
    print("═" * 66)
