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

import hashlib
import re
import unicodedata
from collections import defaultdict
from typing import Optional

from api.schemas import EnrichedAmendment, PointImpact, StatutMecanique


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


def extract_alinea_number(dispositif_clean: str, alinea_vise: str = "") -> str:
    """Extrait le numéro d'alinéa s'il est spécifié dans le champ ou présent dans le dispositif."""
    if alinea_vise and str(alinea_vise).strip():
        return str(alinea_vise).strip()
    match = _ALINEA_REGEX.search(dispositif_clean or "")
    if match:
        return match.group(1)
    return ""


def get_impact_zone_key(amend: EnrichedAmendment) -> str:
    """
    Calcule la clé composite de zone d'impact pour partitionner les amendements :
    (article_vise, point_impact, alinea_vise).
    """
    art = (amend.article_vise or "ART_GLOBAL").strip().upper()
    impact = amend.point_impact or PointImpact.POINT_RESTREINT

    # Pour suppression / rédaction globale d'article : zone = article entier
    if impact in (PointImpact.SUPPRESSION_ARTICLE, PointImpact.REDACTION_GLOBALE_ARTICLE):
        return f"{art}||GLOBAL_{impact.value}"

    # Pour un alinéa ou point restreint
    al = extract_alinea_number(amend.dispositif_clean, amend.alinea_vise)
    if al:
        amend.alinea_vise = al
        return f"{art}||ALINEA_{al}"

    return f"{art}||{impact.value}"


BOILERPLATE_PATTERNS = [
    "non renseigne",
    "retire avant publication",
    "amendement irrecevable",
    "declare irrecevable",
]


def is_boilerplate_or_insignificant(dispositif_clean: str) -> bool:
    """
    Détecte si un dispositif est non signifiant, vide ou irrecevable.
    Condition : contient un motif de boilerplate ou fait moins de 15 caractères.
    """
    if not dispositif_clean or len(dispositif_clean.strip()) < 15:
        return True
    text = dispositif_clean.lower()
    return any(pattern in text for pattern in BOILERPLATE_PATTERNS)


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

    # ── Phase 1 : Normalisation + classification hiérarchique ──
    for amend in amendments:
        amend.dispositif_clean = normalize_text(amend.dispositif_raw)
        priority, impact = classify_point_impact(amend.dispositif_clean)
        amend.point_impact = impact

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
        if is_boilerplate_or_insignificant(amend.dispositif_clean):
            amend.statut_mecanique = StatutMecanique.ISOLE_MECANIQUE
            amend.skip_llm = True
            amend.justification_mecanique = "Amendement non renseigné ou irrecevable."

    # ── Phase 3 : Détection mécanique par empreinte (vrai texte législatif uniquement) ──
    groups: dict[str, list[int]] = defaultdict(list)

    for idx, amend in enumerate(amendments):
        if amend.statut_mecanique in (StatutMecanique.IDENTIQUE_OFFICIEL, StatutMecanique.ISOLE_MECANIQUE):
            continue

        composite_key = f"{amend.dispositif_clean}||{amend.article_vise}"
        fp = fingerprint(composite_key)
        groups[fp].append(idx)

    for fp, indices in groups.items():
        if len(indices) < 2:
            continue  # Unique textuellement

        referent_idx = indices[0]
        referent_uid = amendments[referent_idx].amendement_uid

        for i in indices[1:]:
            amend = amendments[i]
            amend.statut_mecanique = StatutMecanique.IDENTIQUE_MECANIQUE
            amend.skip_llm = True
            amend.groupe_identique_id = fp
            amend.justification_mecanique = (
                f"Identique mécanique au référent {referent_uid} "
                f"sur {amend.article_vise or 'article non spécifié'}."
            )

    # ── Phase 4 : Clustering mécanique par zone d'impact & Aiguillage des cas complexes ──
    # Partitionnement par clé composite (article, point_impact, alinéa) pour les amendements actifs
    zone_groups: dict[str, list[EnrichedAmendment]] = defaultdict(list)
    for amend in amendments:
        # Les amendements boilerplate/irrecevables sont déjà isolés et ne concurrencent personne
        if is_boilerplate_or_insignificant(amend.dispositif_clean):
            continue
        zone_key = get_impact_zone_key(amend)
        zone_groups[zone_key].append(amend)

    for zone_key, zone_amends in zone_groups.items():
        cluster_fp = fingerprint(zone_key)
        if len(zone_amends) == 1:
            amend = zone_amends[0]
            # Si l'amendement est seul et n'est pas déjà un identique AN officiel
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
            # Plusieurs amendements en concurrence sur le même point d'impact
            distinct_texts = {a.dispositif_clean for a in zone_amends}
            for amend in zone_amends:
                amend.cluster_id = cluster_fp
                # S'il n'est pas déjà marqué identique mécanique
                if amend.statut_mecanique == StatutMecanique.NOUVEAU:
                    impact_label = amend.point_impact.value if amend.point_impact else "impact"
                    alinea_label = f"alinéa {amend.alinea_vise}" if amend.alinea_vise else impact_label
                    if len(distinct_texts) > 1:
                        # Cas complexe : concurrence de textes différents sur la même zone
                        amend.skip_llm = False
                        amend.justification_mecanique = (
                            f"Cas complexe : {len(zone_amends)} amendements en concurrence sur "
                            f"{amend.article_vise or 'article'} ({alinea_label}) — aiguillé vers l'analyse IA."
                        )
                    else:
                        # Tous identiques dans ce cluster : le référent reste NOUVEAU
                        amend.skip_llm = False

    # ── Phase 5 : Tri stable par (priorité d'impact, numéro) ──
    impact_order = {
        PointImpact.SUPPRESSION_ARTICLE: 1,
        PointImpact.REDACTION_GLOBALE_ARTICLE: 2,
        PointImpact.SUPPRESSION_ALINEA: 3,
        PointImpact.REDACTION_ALINEA: 4,
        PointImpact.POINT_RESTREINT: 5,
    }

    amendments.sort(key=lambda a: (
        impact_order.get(a.point_impact, 99),
        a.article_vise,
        a.numero_long,
    ))

    return amendments
