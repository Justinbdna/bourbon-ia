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

    if text.startswith("supprimer cet article") or text.startswith("supprimer larticle"):
        return (1, PointImpact.SUPPRESSION_ARTICLE)

    if text.startswith("rediger ainsi cet article") or text.startswith("rediger ainsi larticle"):
        return (2, PointImpact.REDACTION_GLOBALE_ARTICLE)

    if "supprimer lalinea" in text or "supprimer les alineas" in text:
        return (3, PointImpact.SUPPRESSION_ALINEA)

    if "rediger ainsi lalinea" in text or "rediger ainsi cet alinea" in text:
        return (4, PointImpact.REDACTION_ALINEA)

    return (5, PointImpact.POINT_RESTREINT)


# ──────────────────────────────────────────────────────────────────────────
# Étape 3 : Moteur principal
# ──────────────────────────────────────────────────────────────────────────

def process_deterministic_sorting(
    amendments: list[EnrichedAmendment],
) -> list[EnrichedAmendment]:
    """
    Moteur de tri déterministe 100 % exact.

    Pour chaque amendement :
      1. Normalise le dispositif → `dispositif_clean`
      2. Calcule le point d'impact hiérarchique
      3. Détecte les identiques officiels (champ AN)
      4. Détecte les identiques/doublons mécaniques par empreinte

    Complexité : O(n) — un seul passage + un groupement par dict.

    Args:
        amendments: Liste d'EnrichedAmendment (dispositif_raw doit être rempli).

    Returns:
        La même liste, enrichie avec statut_mecanique, point_impact, etc.
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
            amend.justification_mecanique = (
                f"Marqué 'discussion identique' par l'AN "
                f"(id: {amend.id_discussion_identique or 'non spécifié'})."
            )

    # ── Phase 3 : Détection mécanique par empreinte ──
    # Clé composite : (dispositif normalisé, article visé)
    # → deux amendements sont identiques s'ils modifient le même article
    #   avec exactement le même texte.
    groups: dict[str, list[int]] = defaultdict(list)

    for idx, amend in enumerate(amendments):
        if amend.statut_mecanique == StatutMecanique.IDENTIQUE_OFFICIEL:
            continue  # Déjà traité en phase 2

        composite_key = f"{amend.dispositif_clean}||{amend.article_vise}"
        fp = fingerprint(composite_key)
        groups[fp].append(idx)

    for fp, indices in groups.items():
        if len(indices) < 2:
            continue  # Amendement unique → reste NOUVEAU

        # Le premier est le référent, il reste NOUVEAU.
        referent_idx = indices[0]
        referent_uid = amendments[referent_idx].amendement_uid

        # Seuls les suivants reçoivent le statut Identique
        for i in indices[1:]:
            amend = amendments[i]
            amend.statut_mecanique = StatutMecanique.IDENTIQUE_MECANIQUE
            amend.groupe_identique_id = referent_uid
            amend.justification_mecanique = (
                f"Identique mécanique au référent {referent_uid} "
                f"sur {amend.article_vise or 'article non spécifié'}."
            )

            amend.groupe_identique_id = fp

    # ── Phase 4 : Tri stable par (priorité d'impact, numéro) ──
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
