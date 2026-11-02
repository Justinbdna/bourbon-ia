"""
api/deterministic_engine.py — Moteur de tri déterministe Bourbon.IA
===================================================================
Détection 100 % mécanique (zéro LLM) des identiques et doublons.

Règle métier absolue (rappel AGENTS.md) :
  « La logique de tri algorithmique prime TOUJOURS sur l'IA. »
  « L'IA est utilisée EXCLUSIVEMENT pour détecter les Identiques,
    Doublons et Incompatibilités QUE le moteur mécanique n'a pas captés. »

Ce module garantit donc la détection exacte (0 % faux positifs) avant
que le LLM ne soit sollicité sur le delta restant.

Pipeline :
  1. Normalisation textuelle (strip HTML, lowercase, ponctuation, espaces)
  2. Détection des identiques officiels (champ AN `discussionIdentique`)
  3. Détection des identiques mécaniques (même dispositif nettoyé + même article)
  4. Détection des doublons (identique + même auteur)
"""

from __future__ import annotations

import collections
import hashlib
import html
import re
import unicodedata
from collections import defaultdict
from typing import Any, Optional, Union

from api.schemas import EnrichedAmendment, PointImpact, StatutMecanique

try:
    from api.legal_chapeau_parser import (
        parse_chapeau,
        calculer_priorite_derouleur,
        auditer_recevabilite_art40,
    )
except ModuleNotFoundError:
    from legal_chapeau_parser import (
        parse_chapeau,
        calculer_priorite_derouleur,
        auditer_recevabilite_art40,
    )

try:
    from api.deputes_resolver import resolve_signataires, MAPPING_ORGANES_XVII
except ModuleNotFoundError:
    try:
        from deputes_resolver import resolve_signataires, MAPPING_ORGANES_XVII
    except Exception:
        def resolve_signataires(x): return {"auteurs_formatte": str(x) if x else "", "groupe_principal": "", "est_rapporteur": False}
        MAPPING_ORGANES_XVII = {}


# ──────────────────────────────────────────────────────────────────────────
# Étape 1 : Normalisation textuelle
# ──────────────────────────────────────────────────────────────────────────

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_ENTITY_RE = re.compile(r"&[#\w]+;")
_WHITESPACE_RE = re.compile(r"\s+")
_PUNCTUATION_RE = re.compile(r"[^\w\s]", re.UNICODE)


def normalize_text(raw_html: str) -> str:
    """
    Transforme un dispositif HTML brut en texte normalisé pour comparaison exacte.

    Pipeline :
      1. Suppression des balises HTML (<p>, <br/>, etc.)
      2. Décodage des entités HTML (&amp; → &, &#x00E9; → é, &nbsp; → espace)
      3. Normalisation Unicode (NFC → décomposition puis recomposition)
      4. Passage en minuscules
      5. Suppression de toute la ponctuation
      6. Collapse des espaces multiples en un seul
      7. Strip final
    """
    if not raw_html:
        return ""

    text = _HTML_TAG_RE.sub(" ", raw_html)
    text = _HTML_ENTITY_RE.sub(" ", text)
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    text = _PUNCTUATION_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def fingerprint(text: str) -> str:
    """Génère un hash SHA-256 court (16 premiers caractères) d'un texte normalisé."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ──────────────────────────────────────────────────────────────────────────
# Étape 2 : Classification hiérarchique (Théorie du classement AN)
# ──────────────────────────────────────────────────────────────────────────

def classify_point_impact(dispositif_clean: str) -> tuple[int, PointImpact]:
    """
    Détermine le point d'impact d'un amendement en analysant son chapeau.

    Returns:
        (priorité, PointImpact) — priorité 1 = la plus élevée (suppression article).
    """
    text = dispositif_clean.lower()

    if (
        "supprimer cet article" in text
        or "supprimer l article" in text
        or "supprimer larticle" in text
        or re.search(r"\b(?:cet\s+article|l\s*article(?:\s+(?:premier|1er|unique|\d+))?)\s+est\s+supprim[eé]\b", text)
    ):
        return (1, PointImpact.SUPPRESSION_ARTICLE)

    if (
        "rediger ainsi cet article" in text
        or "rediger ainsi l article" in text
        or "rediger ainsi larticle" in text
        or "rédiger ainsi cet article" in text
        or "rédiger ainsi l article" in text
        or "rédiger ainsi larticle" in text
    ):
        return (2, PointImpact.REDACTION_GLOBALE_ARTICLE)

    if (
        re.search(r"supprimer\s+l\s*alin[eé]as?", text)
        or re.search(r"supprimer\s+les\s+alin[eé]as?", text)
        or "supprimer lalinea" in text
    ):
        return (3, PointImpact.SUPPRESSION_ALINEA)

    if (
        re.search(r"r[eé]diger\s+ainsi\s+(?:l|cet)?\s*alin[eé]as?", text)
        or "rediger ainsi lalinea" in text
    ):
        return (4, PointImpact.REDACTION_ALINEA)

    return (5, PointImpact.POINT_RESTREINT)


_ALINEA_REGEX = re.compile(r"\balin[eé]as?\s*(\d+)", re.IGNORECASE)

_STOPWORDS_CIBLE = {
    "le", "la", "les", "de", "du", "des", "un", "une", "au", "aux", "a", "en",
    "et", "ou", "par", "pour", "dans", "sur", "avec", "ce", "cet", "cette", "ces",
    "son", "sa", "ses", "leur", "leurs", "meme", "memes", "suivant", "suivante",
    "suivants", "suivantes", "mot", "mots", "nombre", "nombres", "montant", "montants",
    "date", "dates", "annee", "annees", "reference", "references", "phrase", "alinea",
    "alineas", "article", "premiere", "seconde", "deuxieme", "troisieme", "derniere",
    "occurrence", "occurrences", "completer", "inserer", "rediger", "ainsi",
    "substituer", "remplacer", "supprimer", "ajouter", "present", "presente",
    "gouvernement", "remet", "parlement", "delai", "compter", "promulgation",
    "rapport", "relatif", "relative", "olympiques", "paralympiques", "hiver", "jeux",
}


def extract_alinea_number(dispositif_clean: str, alinea_vise: str = "") -> str:
    """Extrait le numéro d'alinéa s'il est spécifié dans le champ ou présent dans le dispositif."""
    if alinea_vise and str(alinea_vise).strip():
        return str(alinea_vise).strip()
    match = _ALINEA_REGEX.search(dispositif_clean or "")
    if match:
        return match.group(1)
    return ""


def extract_sub_target(dispositif_clean: str) -> str:
    """
    Extrait la sous-cible légistique précise d'un amendement POINT_RESTREINT
    (mot substitué, insertion après un mot, insertion après un alinéa, etc.)
    afin d'isoler mécaniquement les amendements visant des endroits distincts.
    """
    if not dispositif_clean:
        return ""
    s = unicodedata.normalize("NFKD", dispositif_clean).encode("ASCII", "ignore").decode("utf-8").lower()
    chapeau = s[:140]

    if re.search(r"\bapres\s+l\s*alineas?\s+\d+\s+inserer\b", chapeau):
        return "INSERER_APRES_ALINEA"
    if re.search(r"\bavant\s+l\s*alineas?\s+\d+\s+inserer\b", chapeau):
        return "INSERER_AVANT_ALINEA"
    if re.search(r"\bcompleter\s+(?:cet\s+article|l\s*article|l\s*alinea\s+unique)\b", chapeau):
        return "COMPLETER_ARTICLE"

    m = re.search(
        r"(?:substituer|remplacer)\s+(?:au|aux|le|la|les|a\s+la)\s+"
        r"(?:mot|mots|nombre|nombres|montant|montants|date|dates|annee|annees|reference|references)\s+"
        r"([a-z0-9\s]{1,40})",
        chapeau,
    )
    if m:
        words = [w for w in m.group(1).split() if w not in _STOPWORDS_CIBLE][:2]
        if words:
            return "SUBST_" + "_".join(words)

    m = re.search(
        r"apres\s+(?:le\s+mot|les\s+mots|l\s+annee|la\s+reference|"
        r"la\s+\w+\s+occurrence\s+(?:du\s+mot|de\s+l\s+annee|des\s+mots))\s+"
        r"([a-z0-9\s]{1,30})",
        chapeau,
    )
    if m:
        words = [w for w in m.group(1).split() if w not in _STOPWORDS_CIBLE][:2]
        if words:
            return "APRES_MOT_" + "_".join(words)

    m = re.search(
        r"supprimer\s+(?:le\s+mot|les\s+mots|la\s+fin\s+de|la\s+\w+\s+phrase|"
        r"les\s+\w+\s+occurrences\s+des\s+mots)\s+"
        r"([a-z0-9\s]{1,30})",
        chapeau,
    )
    if m:
        words = [w for w in m.group(1).split() if w not in _STOPWORDS_CIBLE][:2]
        if words:
            return "SUPPR_MOT_" + "_".join(words)

    if re.search(r"\bau\s+debut\s+de\b", chapeau):
        return "DEBUT"
    if re.search(r"\brediger\s+ainsi\s+la\s+fin\b", chapeau):
        return "FIN_PHRASE"

    return ""


def _content_keywords(text: str) -> set[str]:
    """Extrait les mots-clés substantiels (>= 5 lettres, hors stopwords légistiques) d'un dispositif."""
    s = unicodedata.normalize("NFKD", text or "").encode("ASCII", "ignore").decode("utf-8").lower()
    return {w for w in s.split() if len(w) >= 5 and not w.isdigit() and w not in _STOPWORDS_CIBLE}


def get_impact_zone_key(amend: EnrichedAmendment) -> str:
    """
    Calcule la clé composite de zone d'impact pour partitionner les amendements :
    (commission_ref, article_vise, point_impact, alinea_vise, sous_cible).
    """
    art = (amend.article_vise or "ART_GLOBAL").strip().upper()
    comm = (amend.commission_ref or "").strip().upper()
    prefix = f"{comm}||{art}" if comm else art
    impact = amend.point_impact or PointImpact.POINT_RESTREINT

    # Pour suppression / rédaction globale d'article : zone = article entier
    if impact in (PointImpact.SUPPRESSION_ARTICLE, PointImpact.REDACTION_GLOBALE_ARTICLE):
        return f"{prefix}||GLOBAL_{impact.value}"

    sub = extract_sub_target(amend.dispositif_clean) if impact == PointImpact.POINT_RESTREINT else ""

    # Pour un alinéa ou point restreint
    al = extract_alinea_number(amend.dispositif_clean, amend.alinea_vise)
    if al:
        amend.alinea_vise = al
        return f"{prefix}||ALINEA_{al}||{sub}" if sub else f"{prefix}||ALINEA_{al}"

    return f"{prefix}||{impact.value}||{sub}" if sub else f"{prefix}||{impact.value}"


BOILERPLATE_PATTERNS = [
    "non renseigne",
    "retire avant publication",
    "amendement irrecevable",
    "declare irrecevable",
    "irrecevable art",
    "irrecevable",
]


def is_boilerplate_or_empty(text: str) -> bool:
    """
    Détecte si un dispositif est non signifiant, vide, retiré ou irrecevable.
    Normalise le texte en supprimant totalement les accents et la ponctuation :
    unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8').lower().strip()
    Condition : contient un motif de boilerplate ou fait moins de 15 caractères.
    """
    if not text:
        return True

    clean_no_html = _HTML_TAG_RE.sub(" ", str(text))
    deaccented = (
        unicodedata.normalize("NFKD", clean_no_html)
        .encode("ASCII", "ignore")
        .decode("utf-8")
        .lower()
        .strip()
    )
    deaccented = _PUNCTUATION_RE.sub(" ", deaccented)
    deaccented = _WHITESPACE_RE.sub(" ", deaccented).strip()

    if len(deaccented) < 15:
        return True

    return any(pattern in deaccented for pattern in BOILERPLATE_PATTERNS)


# Rétrocompatibilité
is_boilerplate_or_insignificant = is_boilerplate_or_empty


_ORGANE_UID_RE = re.compile(r"PO\d+")


def _cle_auteur(amend: EnrichedAmendment) -> str:
    """
    Identifie « même auteur, même examen » pour la détection des doublons.

    Auteur : référence acteur AN si connue, sinon libellé brut
    (« Élisa Martin (LFI-NFP) »), sinon nom et prénom. Chaîne vide si l'auteur
    est inconnu : on ne conclut alors jamais au doublon (0 % faux positifs).

    Examen : l'organe saisi (commission). Un même texte redéposé par le même
    député dans une AUTRE commission (avis puis fond) est un dépôt normal,
    pas un doublon à supprimer.
    """
    if amend.auteur_ref:
        auteur = f"ref:{amend.auteur_ref}"
    else:
        brut = amend.auteurs_raw[0] if amend.auteurs_raw else f"{amend.auteur_prenom} {amend.auteur_nom}"
        sans_accents = unicodedata.normalize("NFKD", brut).encode("ASCII", "ignore").decode("utf-8")
        nom = normalize_text(sans_accents)
        if not nom:
            return ""
        auteur = f"nom:{nom}"
    m = _ORGANE_UID_RE.search(amend.amendement_uid or "")
    organe = amend.commission_ref or (m.group(0) if m else "")
    return f"{organe}|{auteur}"


def qualify_irrecevabilite(amend: EnrichedAmendment) -> str:
    """
    Qualifie précisément l'irrecevabilité d'un amendement selon les règles de l'AN :
      - Article 40 de la Constitution : irrecevabilité financière (aggravation d'une charge publique)
      - Article 45 de la Constitution / Article 98 du Règlement : cavalier législatif ou règle de l'entonnoir
      - Autres irrecevabilités / retraits
    """
    raw = amend.raw_dict if isinstance(amend.raw_dict, dict) else {}
    corps = raw.get("corps") if isinstance(raw.get("corps"), dict) else {}
    cartouche = str(corps.get("cartoucheInformatif") or raw.get("cartoucheInformatif") or "")
    cycle = raw.get("cycleDeVie") if isinstance(raw.get("cycleDeVie"), dict) else {}
    etat_chrono = cycle.get("etatChronologique") if isinstance(cycle.get("etatChronologique"), dict) else {}
    mention = str(etat_chrono.get("mention") or cycle.get("mention") or "")
    code_chrono = str(etat_chrono.get("code") or cycle.get("code") or "")
    sort = str(raw.get("sort") or "")

    corpus_irr = f"{amend.dispositif_raw} {amend.dispositif_clean} {cartouche} {mention} {code_chrono} {sort}".lower()

    if (
        "art. 40" in corpus_irr
        or "article 40" in corpus_irr
        or "art 40" in corpus_irr
        or "irr40" in corpus_irr
        or "charge financière" in corpus_irr
        or "charge publique" in corpus_irr
    ):
        return "Irrecevable (Art. 40 - Recevabilité financière)"

    if (
        "art. 45" in corpus_irr
        or "article 45" in corpus_irr
        or "art 45" in corpus_irr
        or "irr45" in corpus_irr
        or "art. 98" in corpus_irr
        or "article 98" in corpus_irr
        or "art 98" in corpus_irr
        or "cavalier" in corpus_irr
        or "entonnoir" in corpus_irr
    ):
        return "Irrecevable (Art. 45/98 - Cavalier législatif / Entonnoir)"

    return "Amendement non renseigné, retiré ou irrecevable."


# ──────────────────────────────────────────────────────────────────────────
# Utilitaires de nettoyage HTML et de détection légistique
# ──────────────────────────────────────────────────────────────────────────

def strip_html_for_display(text: Any) -> str:
    """
    Nettoie rigoureusement le HTML et décode toutes les entités pour l'affichage parlementaire.
    Supprime les balises <p>, <br>, etc., et décode &nbsp;, &#160;, &#x2011;, &laquo;, &raquo;, &rsquo;, etc.
    """
    if not text:
        return ""
    # Unescape avant ET après suppression des balises pour traiter le HTML doublement échappé (&lt;p...&gt;)
    s = html.unescape(str(text))
    s = re.sub(r"</p>\s*<p[^>]*>", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"</(?:p|div)>", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = s.replace("\xa0", " ").replace("&#160;", " ").replace("&nbsp;", " ")
    s = s.replace("&#x2011;", "‑")
    s = s.replace("&laquo;", "«").replace("&raquo;", "»")
    s = s.replace("&rsquo;", "’").replace("&lsquo;", "‘")
    s = s.replace("&quot;", '"').replace("&apos;", "'")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n\n", s)
    return s.strip()


strip_html_tags = strip_html_for_display


def detect_gage_financier(dispositif: Any, raw_dict: Optional[dict] = None) -> bool:
    """
    Détecte la présence d'une formule de gage financier au titre de l'Article 40
    de la Constitution ("perte de recettes", "compensée à due concurrence",
    "création d'une taxe additionnelle", "articles 575 et 575 A").
    """
    if raw_dict:
        am = raw_dict.get("amendement", raw_dict)
        if str(am.get("cycleDeVie", {}).get("soumisArticle40", "")).lower() == "true":
            return True

    if not dispositif:
        return False

    s_norm = unicodedata.normalize("NFKD", str(dispositif)).encode("ASCII", "ignore").decode("utf-8").lower()
    gage_patterns = [
        "perte de recettes",
        "compensee a due concurrence",
        "creation d'une taxe additionnelle",
        "creation d une taxe additionnelle",
        "articles 575 et 575 a",
        "article 575",
        "taxe additionnelle",
        "gage financier",
    ]
    return any(p in s_norm for p in gage_patterns)


def get_article_sort_key(target: Union[EnrichedAmendment, str, dict]) -> tuple[int, int, int]:
    """
    Retourne un tuple de tri numérique et parlementaire pour un article :
      (num_article, pos_article, sous_rang)

    Règles :
      - Préambule / Titre / Intitulé : num_article = 0 -> (0, 0, 0)
      - 'PREMIER', '1ER', 'unique', 'UNIQUE' -> num_article = 1
      - Extrait le numéro entier principal (2, 3, 4...)
      - Position relative :
          'AVANT' l'article X -> pos_article = -1, sous_rang = 0
          'A' (sur l'article X lui-même) -> pos_article = 0, sous_rang = 0
          'APRES' l'article X ou article additionnel -> pos_article = 1
            avec sous-rang : bis=1, ter=2, quater=3, quinquies=4, sexies=5...
    """
    if target is None:
        return (9999, 0, 0)

    raw_dict = {}
    if isinstance(target, EnrichedAmendment):
        article_str = target.article_vise or ""
        raw_dict = target.raw_dict or {}
    elif isinstance(target, dict):
        article_str = target.get("article_vise") or target.get("article") or ""
        raw_dict = target
    else:
        article_str = str(target)

    s = article_str.strip()
    if not s:
        return (9999, 0, 0)

    s_norm = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("utf-8").upper()

    # 1. Préambule / Titre / Intitulé
    if any(k in s_norm for k in ("PREAMBULE", "TITRE", "LIMINAIRE", "INTITULE")):
        return (0, 0, 0)

    # 2. Détection du numéro principal de l'article
    num_article = None
    if any(k in s_norm for k in ("PREMIER", "1ER", "UNIQUE")):
        num_article = 1
    else:
        m = re.search(r"\b(\d+)\b", s_norm)
        if m:
            num_article = int(m.group(1))

    # 3. Positionnement relatif (AVANT / A / APRÈS / BIS / etc.)
    division = raw_dict.get("amendement", raw_dict).get("pointeurFragmentTexte", {}).get("division", {}) if isinstance(raw_dict, dict) else {}
    pos_raw = str(division.get("avant_A_Apres") or division.get("avantAApres") or "").strip().upper() if isinstance(division, dict) else ""
    art_add = str(division.get("articleAdditionnel") or "").strip().lower() if isinstance(division, dict) else ""

    is_avant = "AVANT" in s_norm or pos_raw == "AVANT"
    is_apres = "APRES" in s_norm or pos_raw in ("APRES", "APRÈS") or art_add == "true"

    suffix_ranks = {
        "BIS": 1,
        "TER": 2,
        "QUATER": 3,
        "QUINQUIES": 4,
        "SEXIES": 5,
        "SEPTIES": 6,
        "OCTIES": 7,
        "NONIES": 8,
        "DECIES": 9,
    }

    sous_rang = 0
    for suffix, rank in suffix_ranks.items():
        if re.search(rf"\b{suffix}\b", s_norm):
            sous_rang = rank
            is_apres = True
            break

    if num_article is None:
        if is_avant:
            return (0, 0, 0)
        return (9999, 0, 0)

    if is_avant:
        pos_article = -1
        sous_rang = 0
    elif is_apres:
        pos_article = 1
    else:
        pos_article = 0

    return (num_article, pos_article, sous_rang)


article_sort_key = get_article_sort_key


def _get_alinea_int_for_sort(amend: EnrichedAmendment) -> int:
    """Extrait le numéro d'alinéa entier d'un amendement pour l'ordonnancement séquentiel."""
    al_str = extract_alinea_number(amend.dispositif_clean or amend.dispositif_raw, amend.alinea_vise)
    if al_str:
        m = re.search(r"\d+", al_str)
        if m:
            return int(m.group())

    if amend.raw_dict:
        raw = amend.raw_dict
        am = raw.get("amendement", raw)
        al = am.get("pointeurFragmentTexte", {}).get("amendementStandard", {}).get("alinea", {})
        if isinstance(al, dict):
            num = al.get("numero")
            if num is not None:
                m = re.search(r"\d+", str(num))
                if m:
                    return int(m.group())

    return 9999


def get_article_internal_sort_key(amend: EnrichedAmendment) -> tuple:
    """
    Ordre de priorité réglementaire strict de l'Assemblée nationale et du Sénat
    au Dérouleur de séance sur un article donné :
      1. Priorité mathématique au dérouleur (`calculer_priorite_derouleur`) :
         - 10 : Suppression totale de l'article
         - 20 : Rédaction globale de l'article
         - 30 + (alinea_num * 10) + rang_phrase : Corps de l'article (alinéa 1..N, phrase 1..M)
         - 800 : Compléter l'article in fine
         - 900 : Article additionnel
      2. Amendements de commission / rapporteur prioritaires à portée égale
      3. Ordre de dépôt
    """
    derouleur_key = calculer_priorite_derouleur(amend)
    prio_rapporteur = 0 if amend.est_rapporteur else 1

    depot_num = 999999
    if amend.raw_dict:
        am = amend.raw_dict.get("amendement", amend.raw_dict)
        raw_depot = am.get("identification", {}).get("numeroOrdreDepot")
        if raw_depot is not None:
            m = re.search(r"\d+", str(raw_depot))
            if m:
                depot_num = int(m.group())
    if depot_num == 999999 and amend.numero_long:
        m = re.search(r"\d+", str(amend.numero_long))
        if m:
            depot_num = int(m.group())

    return (derouleur_key, prio_rapporteur, depot_num, str(amend.numero_long or amend.amendement_uid))


# ──────────────────────────────────────────────────────────────────────────
# Étape 3 : Moteur principal
# ──────────────────────────────────────────────────────────────────────────

def process_deterministic_sorting(
    amendments: list[EnrichedAmendment],
) -> list[EnrichedAmendment]:
    """
    Moteur de tri déterministe 100 % exact avec clustering mécanique.

    Pour chaque amendement :
      1. Normalise le dispositif → `dispositif_clean`
      2. Calcule le point d'impact hiérarchique
      3. Détecte les identiques officiels (champ AN)
      4. Détecte et isole les textes non signifiants / irrecevables (anti-faux identiques)
      5. Détecte les identiques mécaniques par empreinte exacte (textes signifiants)
      6. Clustering mécanique par zone d'impact & aiguillage des cas complexes :
         - Si amendement unique sur sa zone → ISOLE_MECANIQUE (_skipLLM = True)
         - Si plusieurs amendements aux textes distincts en concurrence → NOUVEAU (_skipLLM = False, aiguillé IA)
      7. Tri stable par hiérarchie de l'Assemblée nationale

    Complexité : O(n) — partitionnements par dicts.
    """

    # ── Phase 1 : Normalisation + classification hiérarchique + résolution députés + gage ──
    for amend in amendments:
        amend.dispositif_clean = normalize_text(amend.dispositif_raw)
        priority, impact = classify_point_impact(amend.dispositif_clean)
        amend.point_impact = impact

        # Analyse syntaxique du chapeau (AN / Sénat) et calcul de priorité au dérouleur
        texte_source = amend.dispositif_raw or amend.dispositif_clean
        chapeau_info = parse_chapeau(texte_source)
        amend.verbe_action = chapeau_info.verbe_action or None
        amend.cible_type = chapeau_info.cible_type or None
        amend.alinea_num = chapeau_info.alinea_num
        amend.rang_phrase = chapeau_info.rang_phrase
        amend.occurrence_mots = chapeau_info.occurrence_mots
        if chapeau_info.alinea_num is not None and not amend.alinea_vise:
            amend.alinea_vise = str(chapeau_info.alinea_num)

        prio_tuple = calculer_priorite_derouleur(amend)
        amend.priorite_derouleur = prio_tuple[0]

        # Audit constitutionnel de recevabilité financière (Article 40) et détection de gage
        audit_40 = auditer_recevabilite_art40(texte_source, amend.raw_dict)
        amend.alerte_recevabilite_art40 = audit_40["alerte_recevabilite_art40"]
        amend.motif_art40 = audit_40["motif_art40"]
        amend.gage_detecte = audit_40["gage_detecte"]
        amend.est_gage = bool(audit_40["gage_detecte"]) or detect_gage_financier(
            texte_source, amend.raw_dict
        )

        # Extraction du rattachement de sous-amendement si présent dans raw_dict
        if not amend.amendement_parent_ref and amend.raw_dict:
            raw = amend.raw_dict
            am_data = raw.get("amendement", raw)
            p_ref = (
                am_data.get("amendementParentRef")
                or raw.get("amendementParentRef")
                or am_data.get("amendement_parent_ref")
                or raw.get("amendement_parent_ref")
            )
            if isinstance(p_ref, dict):
                if p_ref.get("@xsi:nil") != "true" and p_ref.get("@nil") != "true":
                    amend.amendement_parent_ref = p_ref.get("#text") or p_ref.get("uid") or None
            elif isinstance(p_ref, str) and p_ref.strip() and p_ref.lower() not in ("none", "null", "false"):
                amend.amendement_parent_ref = p_ref.strip()

        # Résolution locale des signataires, groupes et qualité de rapporteur
        raw_sig = None
        if isinstance(amend.raw_dict, dict):
            raw_sig = (
                amend.raw_dict.get("signataires")
                or amend.raw_dict.get("amendement", {}).get("signataires")
            )
        src_signataires = (
            raw_sig
            or amend.auteur_ref
            or amend.auteurs_raw
            or amend.auteur_nom
        )
        if src_signataires:
            res_dep = resolve_signataires(src_signataires)
            if res_dep.get("est_rapporteur"):
                amend.est_rapporteur = True
            if res_dep.get("groupe_principal"):
                amend.groupe_politique = res_dep["groupe_principal"]
            if res_dep.get("auteurs_formatte") and not amend.auteurs_raw:
                amend.auteurs_raw = [res_dep["auteurs_formatte"]]

        # Priorité absolue si groupe_politique_ref est présent dans l'amendement
        if amend.groupe_politique_ref and amend.groupe_politique_ref in MAPPING_ORGANES_XVII:
            amend.groupe_politique = MAPPING_ORGANES_XVII[amend.groupe_politique_ref]

    # ── Phase 2 : Détection des identiques officiels (champ AN) ──
    for amend in amendments:
        if amend.est_identique_officiel or amend.id_discussion_identique:
            amend.statut_mecanique = StatutMecanique.IDENTIQUE_OFFICIEL
            amend.skip_llm = True
            amend.justification_mecanique = (
                f"Marqué 'discussion identique' par l'AN "
                f"(id: {amend.id_discussion_identique or 'non spécifié'})."
            )

    # ── Phase 2bis : Filtrage des faux identiques (textes non signifiants / boilerplate) ──
    for amend in amendments:
        if amend.statut_mecanique == StatutMecanique.IDENTIQUE_OFFICIEL:
            continue
        if is_boilerplate_or_empty(amend.dispositif_clean) or is_boilerplate_or_empty(amend.dispositif_raw):
            amend.statut_mecanique = StatutMecanique.ISOLE_MECANIQUE
            amend.skip_llm = True
            amend.alerte_couleur = "gris"
            amend.justification_mecanique = qualify_irrecevabilite(amend)

    # ── Phase 3 : Détection mécanique par empreinte (vrai texte législatif uniquement) ──
    groups: dict[str, list[int]] = defaultdict(list)

    for idx, amend in enumerate(amendments):
        if amend.statut_mecanique in (StatutMecanique.IDENTIQUE_OFFICIEL, StatutMecanique.ISOLE_MECANIQUE):
            continue
        if is_boilerplate_or_empty(amend.dispositif_clean) or is_boilerplate_or_empty(amend.dispositif_raw):
            continue

        composite_key = f"{amend.dispositif_clean}||{amend.article_vise}"
        fp = fingerprint(composite_key)
        groups[fp].append(idx)

    for fp, indices in groups.items():
        if len(indices) < 2:
            continue  # Unique textuellement

        referent_idx = indices[0]
        referent = amendments[referent_idx]
        referent_uid = referent.amendement_uid

        # Premier amendement déposé par chaque auteur (dans une même commission)
        # dans ce groupe : un texte identique redéposé par le MÊME auteur devant
        # la MÊME commission est un doublon (étape 4).
        premier_par_auteur: dict[str, str] = {}
        cle_referent = _cle_auteur(amendments[referent_idx])
        if cle_referent:
            premier_par_auteur[cle_referent] = referent_uid

        for i in indices[1:]:
            amend = amendments[i]
            amend.skip_llm = True
            amend.groupe_identique_id = fp
            cle = _cle_auteur(amend)
            if cle and cle in premier_par_auteur:
                amend.statut_mecanique = StatutMecanique.DOUBLON_MECANIQUE
                amend.alerte_couleur = "orange"
                amend.justification_mecanique = (
                    f"Doublon de {premier_par_auteur[cle]} : même texte, même auteur (à retirer), "
                    f"sur {amend.article_vise or 'article non spécifié'}."
                )
                continue
            if cle:
                premier_par_auteur[cle] = amend.amendement_uid
            amend.statut_mecanique = StatutMecanique.IDENTIQUE_MECANIQUE
            amend.alerte_couleur = "rouge"
            amend.justification_mecanique = (
                f"Identique mécanique au référent {referent_uid} "
                f"sur {amend.article_vise or 'article non spécifié'}."
            )

    # ── Phase 4 : Clustering mécanique par zone d'impact & Aiguillage des cas complexes ──
    # Partitionnement par clé composite (article, point_impact, alinéa) pour les amendements actifs
    zone_groups: dict[str, list[EnrichedAmendment]] = defaultdict(list)
    for amend in amendments:
        # Les amendements boilerplate/irrecevables sont déjà isolés et ne concurrencent personne
        if is_boilerplate_or_empty(amend.dispositif_clean) or is_boilerplate_or_empty(amend.dispositif_raw):
            continue
        zone_key = get_impact_zone_key(amend)
        zone_groups[zone_key].append(amend)

    for zone_key, zone_amends in zone_groups.items():
        cluster_fp = fingerprint(zone_key)
        # Cas 2 — Amendements de suppression d'article : sort 100 % mécanique (skip_llm = True)
        if all(a.point_impact == PointImpact.SUPPRESSION_ARTICLE for a in zone_amends):
            for amend in zone_amends:
                amend.skip_llm = True
                amend.cluster_id = cluster_fp if len(zone_amends) > 1 else None
                if amend.statut_mecanique == StatutMecanique.NOUVEAU:
                    if len(zone_amends) == 1:
                        amend.statut_mecanique = StatutMecanique.ISOLE_MECANIQUE
                        amend.justification_mecanique = (
                            f"Seul amendement déposé sur cette zone d'impact "
                            f"({amend.article_vise or 'article'} - SUPPRESSION_ARTICLE). "
                            f"Aucun concurrent en discussion commune."
                        )
                    else:
                        amend.justification_mecanique = (
                            f"Amendement de suppression d'article sur {amend.article_vise or 'article'} "
                            f"(traitement mécanique sans LLM)."
                        )
            continue

        if len(zone_amends) == 1:
            amend = zone_amends[0]
            # Cas 5 — Orphelin de zone d'impact : seul sur sa cible -> ISOLE_MECANIQUE, skip_llm = True
            if amend.statut_mecanique == StatutMecanique.NOUVEAU:
                amend.statut_mecanique = StatutMecanique.ISOLE_MECANIQUE
                amend.skip_llm = True
                impact_label = amend.point_impact.value if amend.point_impact else "impact"
                alinea_label = f"alinéa {amend.alinea_vise}" if amend.alinea_vise else impact_label
                amend.justification_mecanique = (
                    f"Seul amendement déposé sur cette zone d'impact "
                    f"({amend.article_vise or 'article'} - {alinea_label}). "
                    f"Aucun concurrent en discussion commune."
                )
        else:
            # Plusieurs amendements sur la même zone d'impact
            distinct_texts = {a.dispositif_clean for a in zone_amends}
            # Sécurité droit parlementaire : sur un même article ou un même alinéa existant,
            # deux amendements au vocabulaire différent peuvent être incompatibles (Discussion commune).
            # On ne filtre par recoupement thématique QUE sur les articles additionnels (APRÈS / AVANT ART.)
            # portant sur des demandes de rapport indépendantes.
            is_additive_zone = any(
                tag in zone_key
                for tag in ("APRES ART", "APRÈS ART", "AVANT ART", "APRES L'ARTICLE", "APRÈS L'ARTICLE", "AVANT L'ARTICLE")
            )
            kws_by_id = {id(a): _content_keywords(a.dispositif_clean) for a in zone_amends} if is_additive_zone else {}

            for amend in zone_amends:
                amend.cluster_id = cluster_fp
                if amend.point_impact == PointImpact.SUPPRESSION_ARTICLE:
                    amend.skip_llm = True
                    continue
                # S'il n'est pas déjà marqué identique ou doublon mécanique
                if amend.statut_mecanique == StatutMecanique.NOUVEAU:
                    impact_label = amend.point_impact.value if amend.point_impact else "impact"
                    alinea_label = f"alinéa {amend.alinea_vise}" if amend.alinea_vise else impact_label
                    if len(distinct_texts) > 1:
                        if is_additive_zone:
                            my_kws = kws_by_id.get(id(amend), set())
                            has_topic_overlap = any(
                                len(my_kws & kws_by_id.get(id(other), set())) >= 2
                                for other in zone_amends
                                if other.dispositif_clean != amend.dispositif_clean
                            )
                            if not has_topic_overlap:
                                amend.statut_mecanique = StatutMecanique.ISOLE_MECANIQUE
                                amend.skip_llm = True
                                amend.justification_mecanique = (
                                    f"Seul amendement déposé sur cette zone d'impact "
                                    f"({amend.article_vise or 'article'} - sujet distinct). "
                                    f"Aucun concurrent en discussion commune."
                                )
                                continue
                        # Cas complexe : concurrence de textes différents sur la même zone
                        amend.skip_llm = False
                        amend.justification_mecanique = (
                            f"Cas complexe : {len(zone_amends)} amendements en concurrence sur "
                            f"{amend.article_vise or 'article'} ({alinea_label}) — aiguillé vers l'analyse IA."
                        )
                    else:
                        # Tous identiques dans ce cluster : aucun concurrent de texte distinct -> pas besoin de LLM
                        amend.skip_llm = True
                        amend.justification_mecanique = (
                            f"Chef de file d'amendements identiques sur {amend.article_vise or 'article'} "
                            f"(aucun autre texte concurrent sur cette zone)."
                        )

    # ── Phase 5 : Tri stable officiel (article parlementaire, priorité interne AN, sous-amendements) ──
    amendments.sort(key=lambda a: (
        get_article_sort_key(a),
        get_article_internal_sort_key(a),
    ))

    # Rattachement des sous-amendements : triés immédiatement après leur amendement parent
    parent_map = {}
    for a in amendments:
        parent_map[a.amendement_uid] = a
        if a.numero_long:
            parent_map[a.numero_long] = a

    children_by_parent = defaultdict(list)
    has_parent_in_list = set()
    for a in amendments:
        p_ref = a.amendement_parent_ref
        if p_ref and p_ref in parent_map and parent_map[p_ref].amendement_uid != a.amendement_uid:
            parent_uid = parent_map[p_ref].amendement_uid
            children_by_parent[parent_uid].append(a)
            has_parent_in_list.add(a.amendement_uid)

    if has_parent_in_list:
        ordered_list = []
        visited = set()

        def _add_with_subamendments(item: EnrichedAmendment):
            if item.amendement_uid in visited:
                return
            visited.add(item.amendement_uid)
            ordered_list.append(item)
            for child in children_by_parent.get(item.amendement_uid, []):
                _add_with_subamendments(child)

        for a in amendments:
            if a.amendement_uid not in has_parent_in_list:
                _add_with_subamendments(a)

        # Filet de sécurité pour ne perdre aucun sous-amendement en cas de cycle
        for a in amendments:
            if a.amendement_uid not in visited:
                ordered_list.append(a)

        amendments = ordered_list

    return amendments
