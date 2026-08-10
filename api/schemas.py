"""
api/schemas.py — Modèles Pydantic pour Bourbon.IA
==================================================
Validation et typage des amendements enrichis.
Basé sur la cartographie : docs/DATA_MAPPING_TRICOTEUSES.md

Ces schémas servent de contrat de données entre :
  - Le client Tricoteuses (api/tricoteuses_client.py)
  - Le moteur de tri déterministe (api/deterministic_engine.py)
  - Le front-end React (via l'API FastAPI)
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────────
# Statuts mécaniques (100 % déterministes, zéro LLM)
# ──────────────────────────────────────────────────────────────────────────
class StatutMecanique(str, Enum):
    """Résultat du moteur de tri déterministe."""
    NOUVEAU = "NOUVEAU"
    IDENTIQUE_MECANIQUE = "IDENTIQUE_MECANIQUE"   # Même dispositif, auteurs différents
    DOUBLON_MECANIQUE = "DOUBLON_MECANIQUE"        # Même dispositif, même auteur
    IDENTIQUE_OFFICIEL = "IDENTIQUE_OFFICIEL"      # Marqué par l'AN via discussionIdentique


# ──────────────────────────────────────────────────────────────────────────
# Point d'impact (classification hiérarchique selon la Théorie du classement)
# ──────────────────────────────────────────────────────────────────────────
class PointImpact(str, Enum):
    """Hiérarchie de l'Assemblée nationale pour le classement des amendements."""
    SUPPRESSION_ARTICLE = "SUPPRESSION_ARTICLE"          # Priorité 1
    REDACTION_GLOBALE_ARTICLE = "REDACTION_GLOBALE_ARTICLE"  # Priorité 2
    SUPPRESSION_ALINEA = "SUPPRESSION_ALINEA"            # Priorité 3
    REDACTION_ALINEA = "REDACTION_ALINEA"                # Priorité 4
    POINT_RESTREINT = "POINT_RESTREINT"                  # Priorité 5 (substitution, insertion…)


# ──────────────────────────────────────────────────────────────────────────
# Amendement enrichi (schéma plat, dénormalisé pour le front-end)
# ──────────────────────────────────────────────────────────────────────────
class EnrichedAmendment(BaseModel):
    """
    Amendement enrichi avec données dénormalisées (auteur, groupe, dossier).
    C'est l'objet canonique circulant dans tout le pipeline Bourbon.IA.
    """

    # ── Identifiants ──
    amendement_uid: str = Field(..., description="Clé primaire unique de l'amendement (ex: AMANR5L17...)")
    numero_long: str = Field("", description="Numéro d'affichage officiel (ex: '52')")

    # ── Texte juridique ──
    dispositif_raw: str = Field("", description="Dispositif brut HTML tel que fourni par l'AN")
    dispositif_clean: str = Field("", description="Dispositif nettoyé (sans HTML, normalisé)")
    expose_sommaire: str = Field("", description="Exposé sommaire nettoyé")

    # ── Division / Article visé ──
    article_vise: str = Field("", description="Désignation courte de l'article (ex: 'ART. PREMIER')")
    alinea_vise: str = Field("", description="Numéro de l'alinéa visé (ex: '2')")

    # ── Auteur (dénormalisé depuis AMO 30) ──
    auteur_ref: str = Field("", description="Clé FK vers l'acteur (ex: PA841749)")
    auteur_nom: str = Field("", description="Nom de famille du député")
    auteur_prenom: str = Field("", description="Prénom du député")
    auteur_trigramme: str = Field("", description="Trigramme parlementaire (ex: MCH)")
    auteurs_raw: list[str] = Field(default_factory=list, description="Liste brute des auteurs préservée depuis le frontend")

    # ── Groupe politique (dénormalisé) ──
    groupe_politique_ref: str = Field("", description="Clé FK vers l'organe politique (ex: PO845401)")
    groupe_politique: str = Field("", description="Nom du groupe politique")

    # ── Dossier législatif (dénormalisé) ──
    dossier_ref: str = Field("", description="Clé FK vers le texte de loi (texteLegislatifRef)")
    dossier_titre: str = Field("", description="Titre officiel du projet de loi")

    # ── Champs AN officiels pour détection identiques ──
    est_identique_officiel: bool = Field(False, description="True si l'AN a marqué cet amendement comme discussion identique")
    id_discussion_identique: Optional[str] = Field(None, description="Identifiant du groupe de discussion identique (AN)")

    # ── Résultat du moteur déterministe ──
    statut_mecanique: StatutMecanique = Field(StatutMecanique.NOUVEAU, description="Résultat du tri mécanique")
    point_impact: Optional[PointImpact] = Field(None, description="Classification hiérarchique AN")
    groupe_identique_id: Optional[str] = Field(None, description="Hash du groupe d'identiques (partagé entre les amendements jumeaux)")
    justification_mecanique: str = Field("", description="Explication courte du statut mécanique")
    
    raw_dict: dict = Field(default_factory=dict, description="Données d'origine pour préserver les métadonnées")

    class Config:
        use_enum_values = True
