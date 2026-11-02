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

from pydantic import BaseModel, Field, ConfigDict


# ──────────────────────────────────────────────────────────────────────────
# Statuts mécaniques (100 % déterministes, zéro LLM)
# ──────────────────────────────────────────────────────────────────────────
class StatutMecanique(str, Enum):
    """Résultat du moteur de tri déterministe."""
    NOUVEAU = "NOUVEAU"
    IDENTIQUE_MECANIQUE = "IDENTIQUE_MECANIQUE"   # Même dispositif, auteurs différents
    DOUBLON_MECANIQUE = "DOUBLON_MECANIQUE"        # Même dispositif, même auteur
    IDENTIQUE_OFFICIEL = "IDENTIQUE_OFFICIEL"      # Marqué par l'AN via discussionIdentique
    ISOLE_MECANIQUE = "ISOLE_MECANIQUE"            # Seul sur sa zone d'impact (skip LLM)


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
    amendement_uid: str = Field(..., max_length=150, description="Clé primaire unique de l'amendement (ex: AMANR5L17...)")
    numero_long: str = Field("", max_length=100, description="Numéro d'affichage officiel (ex: '52')")

    # ── Texte juridique ──
    dispositif_raw: str = Field("", max_length=500_000, description="Dispositif brut HTML tel que fourni par l'AN")
    dispositif_clean: str = Field("", max_length=500_000, description="Dispositif nettoyé (sans HTML, normalisé)")
    expose_sommaire: str = Field("", max_length=500_000, description="Exposé sommaire nettoyé")

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

    # ── Commission saisie + corrélation thématique (api/commissions_resolver.py) ──
    # L'uid d'organe est extrait de l'uid de l'amendement (AMANR5L17*PO59051*…),
    # donc résolu hors-ligne, sans appel réseau.
    commission_ref: str = Field("", description="Clé FK vers l'organe saisi (ex: PO59051)")
    commission_libelle: str = Field("", description="Libellé complet de la commission")
    commission_abrege: str = Field("", description="Libellé abrégé (ex: 'Lois', 'Finances')")
    commission_mots_cles: list[str] = Field(
        default_factory=list,
        description="Thèmes du périmètre de la commission RÉELLEMENT présents dans le texte de l'amendement",
    )
    commission_hors_champ: bool = Field(
        False,
        description="True si aucun thème de la commission n'apparaît dans l'amendement "
                    "(signal faible de cavalier législatif, art. 45 — à vérifier par un humain)",
    )

    # ── Champs AN officiels pour détection identiques ──
    est_identique_officiel: bool = Field(False, description="True si l'AN a marqué cet amendement comme discussion identique")
    id_discussion_identique: Optional[str] = Field(None, description="Identifiant du groupe de discussion identique (AN)")

    # ── Résultat du moteur déterministe ──
    statut_mecanique: StatutMecanique = Field(StatutMecanique.NOUVEAU, description="Résultat du tri mécanique")
    point_impact: Optional[PointImpact] = Field(None, description="Classification hiérarchique AN")
    groupe_identique_id: Optional[str] = Field(None, description="Hash du groupe d'identiques (partagé entre les amendements jumeaux)")
    cluster_id: Optional[str] = Field(None, description="Identifiant du cluster de concurrence (même alinéa/zone d'impact)")
    skip_llm: bool = Field(False, description="True si classé mécaniquement sans besoin d'analyse LLM")
    justification_mecanique: str = Field("", description="Explication courte du statut mécanique")
    alerte_couleur: Optional[str] = Field(None, description="Couleur de l'alerte UI (gris, vert, orange, rouge)")
    est_rapporteur: bool = Field(False, description="True si déposé par le rapporteur ou la commission")
    texte_loi_reference: Optional[str] = Field(None, description="Texte initial de l'article de loi de référence")
    amendement_parent_ref: Optional[str] = Field(None, description="Référence de l'amendement parent s'il s'agit d'un sous-amendement")
    est_gage: bool = Field(False, description="True si l'amendement comporte une formule de gage financier au titre de l'Art. 40")
    alerte_recevabilite_art40: bool = Field(
        False,
        description="True si une perte de recettes ou création de charge est détectée sans gage constitutionnel valide (Art. 40)",
    )
    motif_art40: Optional[str] = Field(
        None,
        description="Motif détaillé du risque d'irrecevabilité financière au titre de l'Article 40",
    )
    gage_detecte: Optional[str] = Field(
        None,
        description="Libellé du gage financier constitutionnel détecté (Tabac, Alcool, DGF, Sécurité sociale)",
    )

    # ── Analyse syntaxique du chapeau et ordre au dérouleur (api/legal_chapeau_parser.py) ──
    verbe_action: Optional[str] = Field(None, description="Verbe cardinal d'action du chapeau (SUPPRIMER, REDIGER_AINSI, etc.)")
    cible_type: Optional[str] = Field(None, description="Cible anatomique du chapeau (ARTICLE, ALINEA, PHRASE, MOTS, etc.)")
    alinea_num: Optional[int] = Field(None, description="Numéro de pastille d'alinéa en marge extrait du chapeau")
    rang_phrase: Optional[int] = Field(None, description="Rang numérique de la phrase visée")
    occurrence_mots: Optional[int] = Field(None, description="Nombre ou rang d'occurrences de mots visés")
    priorite_derouleur: Optional[int] = Field(None, description="Priorité mathématique d'appel au dérouleur de séance")
    
    raw_dict: dict = Field(default_factory=dict, description="Données d'origine pour préserver les métadonnées")

    model_config = ConfigDict(use_enum_values=True)


# ──────────────────────────────────────────────────────────────────────────
# Modèles pour l'analyse de surtransposition UE (api/services/analysis)
# ──────────────────────────────────────────────────────────────────────────

class SurtranspositionItemInput(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    amendement_uid: Optional[str] = Field(None, max_length=150)
    dispositif: str = Field("", max_length=500_000)
    expose_sommaire: Optional[str] = Field("", max_length=500_000)
    article_vise: Optional[str] = Field(None, max_length=200)
    celex_id: Optional[str] = Field(None, max_length=100)


class SurtranspositionRequest(BaseModel):
    """Payload pour la route /api/v2/surtransposition."""
    model_config = ConfigDict(use_enum_values=True)
    amendements: Optional[list[dict]] = Field(None, max_length=2000)
    amendement: Optional[dict] = None
    dispositif: Optional[str] = Field(None, max_length=500_000)
    expose_sommaire: Optional[str] = Field(None, max_length=500_000)
    article_vise: Optional[str] = Field(None, max_length=200)
    amendement_uid: Optional[str] = Field(None, max_length=150)
    celex_id: Optional[str] = Field(None, max_length=100)
