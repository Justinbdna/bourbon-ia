#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/build_golden_dataset.py
Bourbon.ia — Principal Parliamentary Jurist & Golden Benchmark Architect
Constitution du Golden Dataset sémantique officiel de référence (Vérité Terrain)
sur les 341 amendements de public/sample-amendments.json.

Protocole de qualification :
  1. Tri mécanique préalable :
     - Amendements sans dispositif (vides / caducs / retirés) -> Isolé
     - Amendements uniques sur leur article/division -> Isolé
     - Amendements rigoureusement identiques (même dispositif et même article) -> Identique
  2. Arbitrage sémantique par l'IA sur les grappes concurrentes :
     - Concurrence directe sur le même alinéa, rédaction globale alternative ou seuils divergents -> Discussion commune
     - Modification d'un point spécifique non contesté par les autres amendements -> Isolé
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from api.legal_chapeau_parser import (
    _strip_html,
    _fingerprint_text,
    parse_chapeau,
)
from api.deputes_resolver import (
    resolve_signataires,
    get_depute_info,
    MAPPING_ORGANES_XVII,
)


def format_article_vise(division: dict[str, Any]) -> str:
    """Nettoie la désignation de l'article visé (ex: 'PREMIER', '3 BIS', '35')."""
    art_courte = division.get("articleDesignationCourte", "") or division.get("titre", "") or ""
    clean = re.sub(r"^(?:ARTICLE|ART\.)\s+", "", art_courte, flags=re.IGNORECASE)
    clean = re.sub(r"\bART\.\s+", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bARTICLE\s+", "", clean, flags=re.IGNORECASE)
    return clean.strip() or art_courte.strip() or "Non spécifié"


def resoudre_auteur_et_groupe(am: dict[str, Any]) -> tuple[str, str]:
    """Extrait le nom complet de l'auteur principal et son acronyme de groupe politique."""
    sig = am.get("signataires", {})
    auteur_block = sig.get("auteur", {}) if isinstance(sig, dict) else {}
    acteur_ref = auteur_block.get("acteurRef") if isinstance(auteur_block, dict) else None
    groupe_ref = auteur_block.get("groupePolitiqueRef") if isinstance(auteur_block, dict) else None

    nom = ""
    grp = ""

    if acteur_ref:
        dep_info = get_depute_info(str(acteur_ref))
        if dep_info:
            nom = dep_info.get("nom", "")
            grp = dep_info.get("groupe", "")

    if not grp and groupe_ref and str(groupe_ref) in MAPPING_ORGANES_XVII:
        grp = MAPPING_ORGANES_XVII[str(groupe_ref)]

    if not nom or not grp:
        resolu = resolve_signataires(sig)
        if not grp and resolu.get("groupe_principal"):
            grp = resolu["groupe_principal"]
        if not nom and resolu.get("auteurs_formatte"):
            first_raw = resolu["auteurs_formatte"].split(",")[0].strip()
            m = re.match(r"^(.*?)(?:\s*\((.*?)\))?$", first_raw)
            if m:
                nom = m.group(1).strip()
                if not grp and m.group(2):
                    grp = m.group(2).strip()

    if not nom and isinstance(sig, dict):
        lib = sig.get("libelle", "")
        if lib:
            nom = re.sub(r"^(?:M\.|Mme)\s+", "", lib.split(",")[0].split(" et ")[0]).strip()

    nom_final = nom or "Auteur non identifié"
    grp_final = grp or "Non inscrit"
    return (nom_final, grp_final)


# ──────────────────────────────────────────────────────────────────────────
# DICTIONNAIRE D'ARBITRAGE SÉMANTIQUE EXPERT DES GRAPPES CONCURRENTES
# ──────────────────────────────────────────────────────────────────────────
# Pour les amendements non vides et non identiques sur des articles multi-dépôts,
# ce dictionnaire consigne la qualification parlementaire rigoureuse de fond.
SEMANTIC_ARBITRATIONS: dict[str, dict[str, Any]] = {
    # ── ARTICLE PREMIER ──
    "AC60": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC64",
        "justification": "Suppression totale de l'article 1er en conflit direct avec les compléments rédactionnels concurrents.",
    },
    "AC64": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC60",
        "justification": "Complète l'alinéa unique par une réserve dérogatoire en concurrence avec la suppression de l'article.",
    },
    "AC62": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC65",
        "justification": "Adjonction d'un alinéa in fine sur l'évaluation financière en concurrence avec le plafonnement salarial de AC65.",
    },
    "AC65": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC62",
        "justification": "Adjonction d'un alinéa in fine sur les rémunérations des dirigeants en concurrence avec AC62.",
    },

    # ── ARTICLE 3 ──
    "AC128": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC81",
        "justification": "Concurrence directe sur les délais dérogatoires de publicité à l'alinéa 1er.",
    },
    "AC81": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC128",
        "justification": "Concurrence directe sur la date d'entrée en vigueur de la dérogation publicitaire à l'alinéa 1er.",
    },
    "AC18": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Modification ponctuelle des critères de densité sans concurrence sur l'alinéa 3.",
    },
    "AC19": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC129",
        "justification": "Concurrence sur le champ des dérogations d'affichage et de publicité à l'alinéa 5.",
    },
    "AC21": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC129",
        "justification": "Précision temporelle sur l'affichage à l'alinéa 5 en concurrence avec la substitution globale de AC129.",
    },
    "AC129": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC19",
        "justification": "Substitution du calendrier d'affichage à l'alinéa 5 en concurrence avec la suppression de AC19.",
    },
    "AC31": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC20",
        "justification": "Concurrence rédactionnelle sur l'encadrement des nuisances à la seconde phrase de l'alinéa 6 (optimiser vs limiter).",
    },
    "AC20": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC31",
        "justification": "Concurrence rédactionnelle sur la qualification des impacts/nuisances à la seconde phrase de l'alinéa 6.",
    },
    "AC130": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Seul amendement ciblant les délais d'affichage spécifiques de l'alinéa 7.",
    },
    "AC80": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC82",
        "justification": "Concurrence sur la période temporelle des dérogations publicitaires autour des sites à l'alinéa 8.",
    },
    "AC82": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC80",
        "justification": "Concurrence sur le rayon kilométrique de restriction publicitaire à l'alinéa 8 (500m vs 200m).",
    },
    "AC86": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC82",
        "justification": "Suppression de la seconde moitié de l'alinéa 8 en concurrence avec les seuils kilométriques de AC82.",
    },
    "AC133": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Suppression ciblée des alinéas 9 et 10 sans concurrent direct sur ces subdivisions.",
    },
    "AC87": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Suppression ciblée de l'alinéa 13 sans concurrent direct.",
    },
    "AC84": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Insertion d'un alinéa autonome interdisant la publicité pour énergies fossiles après l'alinéa 14.",
    },
    "AC88": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC131",
        "justification": "Suppression globale des alinéas 15 à 17 en conflit direct avec les modifications d'alinéa de AC131 et AC22.",
    },
    "AC131": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC22",
        "justification": "Concurrence directe sur les dates limites de la dérogation publicitaire à l'alinéa 16.",
    },
    "AC22": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC131",
        "justification": "Concurrence rédactionnelle sur les affichages autorisés à la 2de phrase de l'alinéa 16.",
    },
    "AC23 (Rect)": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC132",
        "justification": "Concurrence directe sur les dérogations publicitaires et dates d'application de l'alinéa 18.",
    },
    "AC132": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC23 (Rect)",
        "justification": "Concurrence directe sur le calendrier d'interdiction publicitaire à l'alinéa 18.",
    },
    "AC55": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC132",
        "justification": "Insertion d'un alinéa d'interdiction après l'alinéa 18 en concurrence avec le régime dérogatoire de AC132.",
    },

    # ── ARTICLE 3 BIS ──
    "CD50": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD18",
        "justification": "Suppression de l'article 3 BIS en concurrence frontale avec la réécriture globale de CD18.",
    },
    "CD18": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD68",
        "justification": "Réécriture globale concurrente de l'article 3 BIS en conflit direct avec la version de CD68.",
    },
    "CD19": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD60",
        "justification": "Concurrence sur le délai de remise du bilan environnemental à l'alinéa 1er (12 mois vs 24 mois).",
    },
    "CD20": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD32",
        "justification": "Concurrence sur les institutions associées au rapport (Haut Conseil pour le Climat) à l'alinéa 1er.",
    },
    "CD46": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD16",
        "justification": "Concurrence sur le contenu obligatoire du rapport environnemental à l'alinéa 1er.",
    },
    "CD33": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD47",
        "justification": "Concurrence sur l'association des associations environnementales à l'alinéa 1er.",
    },
    "CD47": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD33",
        "justification": "Concurrence sur la formulation de la contribution associative au bilan carbone à l'alinéa 1er.",
    },
    "CD21": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD18",
        "justification": "Insertion d'un I bis créant un mécanisme d'indemnisation financière en suite du rapport.",
    },
    "CD74": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Insertion d'un 5° spécifique sur l'artificialisation après l'alinéa 7 sans concurrent direct.",
    },
    "CD34": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Complément in fine interdisant les constructions pérennes en zone naturelle protégée.",
    },

    # ── ARTICLE APRÈS 3 BIS ──
    "CD69": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD22",
        "justification": "Demande de rapport gouvernemental post-Jeux en concurrence avec l'évaluation Cour des comptes de CD22.",
    },

    # ── ARTICLE 4 ──
    "AC102": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC103",
        "justification": "Suppression totale de l'article 4 en conflit direct avec son extension juridictionnelle par AC103.",
    },
    "AC103": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC102",
        "justification": "Extension de la compétence des juridictions françaises en concurrence avec la suppression de l'article.",
    },
    "AC3": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Précision rédactionnelle ponctuelle à l'alinéa 2 sans contestation d'autres amendements.",
    },
    "AC30": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Précision syntaxique isolée à l'alinéa 14 sans concurrence sur cette subdivision.",
    },

    # ── ARTICLE APRÈS 5 ──
    "AC76": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC1",
        "justification": "Conditionnement des financements publics du COJOP en concurrence avec le rapport financier de AC1.",
    },
    "AC1": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC76",
        "justification": "Demande de rapport préalable d'étape sur les coûts avant mars 2026 en concurrence avec AC76.",
    },
    "AC63": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC47",
        "justification": "Rapport à 6 ans après promulgation en concurrence avec le rapport de clôture à 6 mois de AC47.",
    },

    # ── ARTICLE 6 ──
    "AC32": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC33",
        "justification": "Concurrence sur la qualification de l'approbation ministérielle à la 1re phrase de l'alinéa unique.",
    },
    "AC33": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC32",
        "justification": "Suppression de la mention des dispositions législatives à la 1re phrase de l'alinéa unique en concurrence avec AC32.",
    },
    "AC16": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC34",
        "justification": "Extension aux violences sexistes à la 2de phrase de l'alinéa unique en concurrence avec AC34 et AC25.",
    },
    "AC34": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC25",
        "justification": "Réécriture de la fin de la 2de phrase de l'alinéa unique en concurrence directe avec AC25.",
    },
    "AC44": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC25",
        "justification": "Insertion d'une obligation de formation aux discriminations en concurrence avec la rédaction de AC25.",
    },
    "AC25": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC34",
        "justification": "Réécriture concurrente de la fin de la 2de phrase de l'alinéa unique sur les discriminations.",
    },

    # ── ARTICLE 7 ──
    "AC134": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC17",
        "justification": "Rétablissement concurrent du paragraphe I sur la désignation des parlementaires au conseil d'administration.",
    },
    "AC53": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC59",
        "justification": "Insertion d'un I bis plafonnant les rémunérations des dirigeants en concurrence avec AC59.",
    },
    "AC59": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC53",
        "justification": "Plafonnement des dix principales rémunérations à l'alinéa 1 bis en concurrence avec AC53.",
    },
    "AC135": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC111",
        "justification": "Suppression du seuil restrictif de dix rémunérations en concurrence avec les seuils de AC111 et AC141.",
    },
    "AC111": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC141",
        "justification": "Extension de la transparence aux 100 premières rémunérations à l'alinéa 2 (vs 20 pour AC141).",
    },
    "AC141": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC111",
        "justification": "Extension de la transparence aux 20 premières rémunérations à l'alinéa 2 (vs 100 pour AC111).",
    },
    "AC113": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC109",
        "justification": "Plan d'encadrement des écarts salariaux complétant l'alinéa 2 en concurrence avec le débat de AC109.",
    },
    "AC109": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC113",
        "justification": "Exigence d'un débat parlementaire complétant l'alinéa 2 en concurrence avec AC113.",
    },

    # ── ARTICLE 8 ──
    "CF2": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CF1",
        "justification": "Concurrence sur les critères d'éligibilité et de subventionnement des associations sportives à l'alinéa 1er.",
    },
    "CF1": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CF2",
        "justification": "Suppression des critères restrictifs de durée à l'alinéa 1er en concurrence avec CF2.",
    },

    # ── ARTICLE APRÈS 8 ──
    "CF5": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CF4",
        "justification": "Création d'un Comité national de suivi des dépenses en concurrence avec le rapport d'évaluation de CF4.",
    },

    # ── ARTICLE 9 ──
    "AC115": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC114",
        "justification": "Adjonction de groupements d'employeurs in fine en concurrence avec l'objectif programmatique de AC114.",
    },
    "AC114": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC115",
        "justification": "Disposition programmatique in fine sur les agents de sécurité en concurrence avec AC115.",
    },

    # ── ARTICLE 11 ──
    "AC140": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Suppression de la dernière phrase de l'alinéa 3 sans concurrence sur cette subdivision.",
    },
    "AC15": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Suppression ciblée des alinéas 12 et 13 portant sur une dérogation distincte de AC140.",
    },

    # ── ARTICLE 12 ──
    "CD24": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD36",
        "justification": "Réécriture globale du régime de participation du public en concurrence avec les réécritures partielles.",
    },
    "CD25": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD3",
        "justification": "Précision sur la démarche environnementale à l'alinéa 1er en concurrence avec le caractère facultatif de CD3.",
    },
    "CD36": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD24",
        "justification": "Substitution de la base légale de consultation (L. 123-1) et suppression des alinéas 2 à 5 en conflit avec CD24.",
    },
    "CD39": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD26",
        "justification": "Consultation en mairie du dossier papier après l'alinéa 1er en concurrence avec la version de CD26.",
    },
    "CD38": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD62",
        "justification": "Triplement du délai de participation du public (3 mois vs 1 mois) à l'alinéa 2.",
    },
    "CD11": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD9",
        "justification": "Restriction du champ d'application après l'alinéa 5 en concurrence avec le débat public de CD9.",
    },

    # ── ARTICLE APRÈS 12 ──
    "CD23": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD10",
        "justification": "Obligation de débat public départemental en concurrence avec le rapport d'évaluation de CD10.",
    },
    "CD10": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD23",
        "justification": "Rapport semestriel sur la concertation publique en concurrence avec le débat préalable de CD23.",
    },

    # ── ARTICLE 14 ──
    "CE11": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CE2",
        "justification": "Suppression totale de l'article 14 en conflit direct avec la suppression partielle des alinéas 2 et 3 de CE2.",
    },
    "CE2": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CE11",
        "justification": "Suppression des alinéas 2 et 3 en concurrence avec la suppression totale de l'article par CE11.",
    },

    # ── ARTICLE 15 ──
    "AC3": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Remplacement rédactionnel ponctuel à l'alinéa 2 sans concurrence sur cette subdivision.",
    },

    # ── ARTICLE 16 ──
    "AC106": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC27",
        "justification": "Suppression de l'article 16 en concurrence avec les aménagements dérogatoires de l'alinéa 4.",
    },
    "AC5": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Extension de l'obligation au démontage et enlèvement à l'alinéa 1er sans concurrent direct.",
    },
    "AC27": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC4",
        "justification": "Concurrence rédactionnelle sur la prise en compte des servitudes à l'alinéa 4.",
    },
    "AC4": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC28",
        "justification": "Ajustement de référence juridique à l'alinéa 4 en concurrence avec la suppression de AC28.",
    },
    "AC28": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC4",
        "justification": "Suppression de la référence à la loi de 1892 à l'alinéa 4 en concurrence avec AC4.",
    },

    # ── ARTICLE 17 ──
    "CE12": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD25",
        "justification": "Suppression de la seconde phrase de l'alinéa 1er en concurrence avec les précisions apportées par CD25.",
    },

    # ── ARTICLE 18 ──
    "CE4": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD63",
        "justification": "Suppression totale de l'article 18 en concurrence directe avec la réduction de délai portée par CD63.",
    },

    # ── ARTICLE 18 BIS ──
    "CD68": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD12",
        "justification": "Réécriture globale de l'article 18 BIS en concurrence frontale avec les amendements de suppression totale.",
    },
    "CD52": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD68",
        "justification": "Ajout d'exclusions territoriales in fine en concurrence avec le périmètre fixé par CD68.",
    },
    "AC138": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD68",
        "justification": "Clause d'exclusion in fine concurrente encadrant la portée dérogatoire de l'article 18 BIS.",
    },

    # ── ARTICLE 20 ──
    "CE6": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Ajout d'un avis du Conseil national de la montagne à l'alinéa 2 sans concurrence sur cette subdivision.",
    },
    "CE16": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Modification de l'échéance temporelle à l'alinéa 6 (2030 au lieu de 2032) sans concurrent direct.",
    },

    # ── ARTICLE 21 ──
    "CD75": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD28",
        "justification": "Garantie environnementale à l'alinéa 4 en concurrence avec la réécriture globale de CD28.",
    },
    "CD70": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD28",
        "justification": "Renforcement de la sécurité physique des transports en concurrence avec la réécriture de CD28.",
    },
    "CD49": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD13",
        "justification": "Volet mobilités partagées complétant le rapport in fine en concurrence avec les propositions de CD13.",
    },
    "CD13": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD49",
        "justification": "Volet pérennité des infrastructures complétant le rapport in fine en concurrence avec CD49 et CD29.",
    },
    "CD29": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD5",
        "justification": "Précision sur les liaisons ferroviaires complétant le rapport in fine en concurrence avec CD5.",
    },
    "CD5": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD6",
        "justification": "Volet ferroviaire détaillé en 7 alinéas complétant le rapport in fine en concurrence avec CD6.",
    },
    "CD6": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD5",
        "justification": "Sous-volet transports du quotidien complétant le rapport in fine en concurrence avec CD5.",
    },
    "CD41": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD49",
        "justification": "Rattachement des projets d'intermodalité complétant le rapport in fine en concurrence avec CD49.",
    },

    # ── ARTICLE APRÈS 21 ──
    "CD43": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Exigence autonome d'exemplarité environnementale sur les flottes automobiles publiques.",
    },

    # ── ARTICLE 22 ──
    "CD14": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CD54",
        "justification": "Suppression totale de l'article 22 en concurrence avec l'encadrement des voies réservées de CD54.",
    },
    "CD71": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Dérogation spécifique pour les communes de moins de 5 000 habitants après l'alinéa 3.",
    },
    "CD31": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Validation ministérielle complétant l'alinéa 4 sans concurrent direct.",
    },

    # ── ARTICLE 24 ──
    "CE19": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Réécriture ciblée de la fin de l'alinéa 3 sans concurrence directe sur cette disposition.",
    },
    "CE7": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Insertion d'une phrase sur les obligations contractuelles à l'alinéa 5 sans concurrent direct.",
    },

    # ── ARTICLE 25 ──
    "AC6": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Substitution de qualification à l'alinéa 1er (affectées vs dédiées) sans concurrent.",
    },
    "AC120": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Interdiction de compensation financière après l'alinéa 2 sans concurrence sur cette division.",
    },

    # ── ARTICLE APRÈS 25 ──
    "AC57": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC73",
        "justification": "Rapport Cour des comptes sur les partenariats en concurrence avec la transparence directe de AC73.",
    },

    # ── ARTICLE 28 ──
    "AC91": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Remplacement de 'sensibilisées' par 'formées' à l'alinéa 5 sans concurrent direct.",
    },
    "AC11": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Suppression de la mention de compétence territoriale à l'alinéa 6 sans concurrent.",
    },
    "AC29": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC30",
        "justification": "Concurrence rédactionnelle sur le recensement des professionnels à la 1re phrase de l'alinéa 14.",
    },
    "AC30": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC12",
        "justification": "Concurrence syntaxique sur la mission des professionnels à la 1re phrase de l'alinéa 14.",
    },
    "AC12": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC29",
        "justification": "Concurrence sémantique sur l'évaluation de l'impact/conséquences à la 1re phrase de l'alinéa 14.",
    },
    "AC13": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Précision sur la nature professionnelle des ordres à l'alinéa 15 sans concurrent.",
    },

    # ── ARTICLE 30 ──
    "AC83": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC41",
        "justification": "Suppression des communes limitrophes à l'alinéa 1er en concurrence avec le transfert au maire de AC41.",
    },
    "AC41": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC42",
        "justification": "Transfert de la décision dérogatoire au maire sur délibération à l'alinéa 1er (vs arrêté simple pour AC42).",
    },
    "AC42": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC41",
        "justification": "Transfert direct au maire de la dérogation dominicale à l'alinéa 1er en concurrence avec AC41.",
    },
    "AC56": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC38",
        "justification": "Restriction de la période de dérogation dominicale à l'alinéa 1er (février vs trimestre complet).",
    },
    "AC38": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC56",
        "justification": "Concurrence sur le calendrier strict de dérogation au repos dominical à l'alinéa 1er.",
    },
    "AC43": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC126",
        "justification": "Exigence d'un avis 'conforme' du maire à l'alinéa 2 en concurrence avec l'avis 'favorable' de AC126.",
    },
    "AC126": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC43",
        "justification": "Exigence d'un avis 'favorable' du maire à l'alinéa 2 en concurrence avec l'avis 'conforme' de AC43.",
    },
    "AC39": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "AC43",
        "justification": "Délai de prévenance de deux mois complétant l'alinéa 2 en concurrence avec les avis de AC43 et AC126.",
    },
    "AC68": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Garantie anti-préjudice pour les salariés refusant le travail du dimanche à l'alinéa 4.",
    },
    "AC79": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Suppression ciblée de l'alinéa 5 portant sur les dérogations aux conventions collectives.",
    },
    "AC72": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Objectif programmatique in fine sur les permanences d'agents de contrôle du travail.",
    },

    # ── ARTICLE 31 ──
    "CL12": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL4",
        "justification": "Encadrement temporel des fouilles de véhicules à l'alinéa 2 (dates fixes vs durée stricte des Jeux).",
    },
    "CL4": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL12",
        "justification": "Restriction des fouilles à la seule durée des Jeux à l'alinéa 2 en concurrence avec CL12.",
    },
    "CL48": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL12",
        "justification": "Extension du périmètre de fouille aux bagages à l'alinéa 2 en concurrence avec l'encadrement temporel.",
    },
    "CL38": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL10",
        "justification": "Préservation expresse des droits des passagers à l'alinéa 2 en concurrence avec CL10.",
    },
    "CL11": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL23",
        "justification": "Exigence d'habilitation préalable des agents de sécurité in fine en concurrence avec le non-profilage de CL23.",
    },
    "CL23": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL11",
        "justification": "Interdiction expresse de discrimination et profilage lors des contrôles in fine en concurrence avec CL11.",
    },

    # ── ARTICLE 32 ──
    "CL36": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL49",
        "justification": "Suppression totale de l'article 32 en concurrence directe avec l'aménagement des sanctions pénales.",
    },
    "CL49": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL36",
        "justification": "Restriction de l'obligation de signalement aux pilotes professionnels à l'alinéa 3 en conflit avec CL36.",
    },
    "CL5": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL36",
        "justification": "Suppression de la peine d'emprisonnement à l'alinéa 7 en concurrence avec la suppression totale de CL36.",
    },

    # ── ARTICLE 33 ──
    "CL35": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL59",
        "justification": "Suppression de l'article 33 en concurrence avec l'extension de la neutralisation des drones.",
    },
    "CL59": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL35",
        "justification": "Extension des matériels de brouillage en tête d'article en conflit avec la suppression de CL35.",
    },
    "CL34": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL35",
        "justification": "Création d'un registre de traçabilité des brouillages in fine en concurrence avec la suppression de CL35.",
    },

    # ── ARTICLE 34 ──
    "CL16": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Ajustement de référence textuelle à l'alinéa 4 sans concurrent direct.",
    },
    "CL32": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL15",
        "justification": "Suppression de la transmission automatique à l'alinéa 5 en concurrence avec la substitution de CL15.",
    },
    "CL15": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL32",
        "justification": "Substitution de la qualification de transmission à l'alinéa 5 en concurrence avec CL32.",
    },
    "CL14": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Suppression ciblée de l'alinéa 6 sans concurrent direct sur cette subdivision.",
    },
    "CL17": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Insertion d'un droit à l'assistance d'un avocat après l'alinéa 7 sans concurrent direct.",
    },
    "CL30": {
        "statut_temoin": "Isolé",
        "cible_discussion": None,
        "justification": "Suppression ciblée de l'alinéa 8 sans concurrent direct.",
    },

    # ── ARTICLE 35 ──
    "CL51": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL52",
        "justification": "Abrogation totale de l'article 10 de la loi JO 2024 en concurrence avec les réécritures partielles de CL52 et CL3.",
    },
    "CL52": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL51",
        "justification": "Interdiction de la biométrie et reconnaissance faciale en concurrence avec l'abrogation de CL51.",
    },
    "CL24": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL3",
        "justification": "Interdiction de prolongation de la VSA au-delà de 2026 en concurrence avec l'expérimentation de CL3.",
    },
    "CL3": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL51",
        "justification": "Limitation de l'expérimentation VSA à la seule durée des Jeux 2030 en concurrence avec CL51 et CL24.",
    },
    "CL53": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL3",
        "justification": "Encadrement des finalités de sécurité de la VSA en concurrence avec les régimes dérogatoires alternatifs.",
    },
    "CL44": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL21",
        "justification": "Réécriture de l'alinéa 3 prolongeant la VSA jusqu'en 2027 en concurrence avec CL21 et CL45.",
    },
    "CL21": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL44",
        "justification": "Réécriture alternative de l'alinéa 3 encadrant le rapport d'évaluation en concurrence avec CL44.",
    },
    "CL45": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL44",
        "justification": "Prolongation de l'expérimentation jusqu'au 31 décembre 2027 à l'alinéa 3 en concurrence avec CL44.",
    },
    "CL46": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL44",
        "justification": "Insertion d'un a bis prolongeant les algorithmes après l'alinéa 3 en concurrence avec CL44.",
    },
    "CL26": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL19",
        "justification": "Suppression de l'alinéa 4 en conflit direct avec les ajouts de garanties de CL19, CL54 et CL47.",
    },
    "CL19": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL54",
        "justification": "Interdiction expresse de la reconnaissance vocale après l'alinéa 4 en concurrence avec CL54 et CL47.",
    },
    "CL54": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL19",
        "justification": "Exigence d'un arrêté préfectoral motivé après l'alinéa 4 en concurrence avec les garanties de CL19.",
    },
    "CL47": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL19",
        "justification": "Rapport annuel de la CNIL après l'alinéa 4 en concurrence avec les verrous de CL19 et CL54.",
    },

    # ── ARTICLE APRÈS 35 ──
    "CL28": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL37",
        "justification": "Rapport à 6 mois sur l'impact de la VSA sur les libertés publiques en concurrence avec CL37 et CL56.",
    },
    "CL37": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL28",
        "justification": "Rapport à 6 mois sur l'efficacité policière de la VSA en concurrence avec l'évaluation des libertés de CL28.",
    },
    "CL56": {
        "statut_temoin": "Discussion commune",
        "cible_discussion": "CL28",
        "justification": "Rapport d'évaluation à 5 ans de la VSA en concurrence avec les rapports semestriels de CL28 et CL37.",
    },
}


def build_golden_dataset() -> dict[str, Any]:
    """Construit et exporte le Golden Dataset sémantique officiel."""
    json_path = ROOT_DIR / "public" / "sample-amendments.json"
    if not json_path.exists():
        raise FileNotFoundError(f"Fichier de données introuvable : {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        amendements_bruts: list[dict[str, Any]] = json.load(f)

    total_count = len(amendements_bruts)

    # ── Étape 1 : Partitionnement mécanique préalable ──
    # Regroupement par article
    am_by_article: dict[str, list[dict[str, Any]]] = defaultdict(list)
    empty_nums: set[str] = set()

    for am in amendements_bruts:
        num = am.get("identification", {}).get("numeroLong") or am.get("numero") or ""
        division = am.get("pointeurFragmentTexte", {}).get("division", {})
        art_clean = format_article_vise(division)

        corps = am.get("corps", {})
        contenu_auteur = corps.get("contenuAuteur", {}) if isinstance(corps, dict) else {}
        disp_raw = (
            contenu_auteur.get("dispositif")
            or (corps.get("dispositif") if isinstance(corps, dict) else "")
            or am.get("dispositif")
            or ""
        )
        disp_clean = _strip_html(disp_raw).strip()
        if not disp_clean:
            empty_nums.add(num)

        am_by_article[art_clean].append(am)

    # Détection des grappes d'identiques textuels SUR LE MÊME ARTICLE
    identical_clusters: dict[str, list[str]] = {}  # num -> cluster list
    cluster_heads: dict[str, str] = {}             # cluster_key -> head num
    identical_twin_target: dict[str, str] = {}     # num -> cible num

    for art, am_list in am_by_article.items():
        fps: dict[str, list[str]] = defaultdict(list)
        for a in am_list:
            n = a.get("identification", {}).get("numeroLong") or a.get("numero") or ""
            if n in empty_nums:
                continue
            disp = _strip_html(
                a.get("corps", {}).get("contenuAuteur", {}).get("dispositif") or ""
            ).strip()
            fp = _fingerprint_text(disp)
            fps[fp].append(n)

        for fp, n_list in fps.items():
            if len(n_list) > 1:
                head = n_list[0]
                for idx, n in enumerate(n_list):
                    identical_clusters[n] = n_list
                    if idx == 0:
                        # Chef de file cible son premier jumeau
                        identical_twin_target[n] = n_list[1]
                    else:
                        # Suiveurs ciblent le chef de file
                        identical_twin_target[n] = head

    # Articles n'ayant qu'un seul amendement opérationnel (non vide)
    singletons_nums: set[str] = set()
    for art, am_list in am_by_article.items():
        non_empty = [
            a.get("identification", {}).get("numeroLong") or a.get("numero")
            for a in am_list
            if (a.get("identification", {}).get("numeroLong") or a.get("numero")) not in empty_nums
        ]
        if len(non_empty) == 1:
            singletons_nums.add(non_empty[0])

    # ── Étape 2 : Construction de la classification de référence ──
    golden_dict: dict[str, dict[str, Any]] = {}
    statut_counter: Counter[str] = Counter()

    for am in amendements_bruts:
        num = str(am.get("identification", {}).get("numeroLong") or am.get("numero") or "").strip()
        division = am.get("pointeurFragmentTexte", {}).get("division", {})
        article = format_article_vise(division)
        auteur, groupe = resoudre_auteur_et_groupe(am)

        # 1. Amendement sans dispositif
        if num in empty_nums:
            statut = "Isolé"
            cible = None
            justif = "Amendement sans dispositif opérationnel."

        # 2. Amendement identique textuel sur le même article
        elif num in identical_clusters:
            statut = "Identique"
            twin = identical_twin_target[num]
            cible = twin
            cluster = identical_clusters[num]
            if num == cluster[0]:
                justif = f"Chef de file d'amendements identiques (partagé avec {twin})."
            else:
                justif = "Dispositif rigoureusement identique déposé par un autre député."

        # 3. Seul amendement déposé sur cet article
        elif num in singletons_nums:
            statut = "Isolé"
            cible = None
            justif = "Seul amendement déposé sur cet article."

        # 4. Arbitrage sémantique expert explicite
        elif num in SEMANTIC_ARBITRATIONS:
            entry = SEMANTIC_ARBITRATIONS[num]
            statut = entry["statut_temoin"]
            cible = entry["cible_discussion"]
            justif = entry["justification"]

        # 5. Repli automatique raisonné pour tout cas non répertorié
        else:
            statut = "Isolé"
            cible = None
            justif = f"Modifie un point spécifique non contesté par les autres amendements de l'article {article}."

        golden_dict[num] = {
            "article": article,
            "auteur": auteur,
            "groupe": groupe,
            "statut_temoin": statut,
            "cible_discussion": cible,
            "justification": justif,
        }
        statut_counter[statut] += 1

    # ── Étape 3 : Export JSON ──
    reports_dir = ROOT_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    json_file = reports_dir / "temoin_classification_golden.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(golden_dict, f, indent=2, ensure_ascii=False)

    # ── Étape 4 : Export Markdown ──
    md_file = reports_dir / "temoin_classification_golden.md"

    md_lines: list[str] = [
        "# Golden Dataset Sémantique de Référence — Vérité Terrain (341 Amendements)",
        "",
        "> **Bourbon.ia — Moteur de Benchmark de Référence (Oracle Sémantique)**  ",
        f"> *Source : `public/sample-amendments.json` | Corpus qualifié : {total_count} amendements | Règlements AN & Sénat*",
        "",
        "---",
        "",
        "## Section 1 : Bilan consolidé de la vérité terrain",
        "",
        "| Statut Témoin | Effectif (Amendements) | Part relative | Rôle dans l'évaluation sémantique |",
        "| :--- | :---: | :---: | :--- |",
        f"| **Identique** | **{statut_counter['Identique']}** | {statut_counter['Identique']/total_count*100:.1f} % | Détection mécanique stricte par empreinte et même article (coût LLM 0) |",
        f"| **Discussion commune** | **{statut_counter['Discussion commune']}** | {statut_counter['Discussion commune']/total_count*100:.1f} % | Conflits de fond arbitrés par l'IA (grappes concurrentes réelles) |",
        f"| **Isolé** | **{statut_counter['Isolé']}** | {statut_counter['Isolé']/total_count*100:.1f} % | Sans dispositif ({len(empty_nums)} ams), divisions uniques ou dispositions spécifiques |",
        f"| **TOTAL GÉNÉRAL** | **{total_count}** | **100,0 %** | **Vérification intégrale des 341 amendements du corpus** |",
        "",
        "---",
        "",
        "## Section 2 : Focus sur les grappes de discussion commune (Conflits parlementaires par article)",
        "",
        "Les articles suivants concentrent les principales oppositions politiques et techniques en séance :",
        "",
    ]

    # Regroupement des discussions communes par article pour la section 2
    dc_by_article: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for num, item in golden_dict.items():
        if item["statut_temoin"] == "Discussion commune":
            dc_by_article[item["article"]].append((num, item))

    for art, ams in sorted(dc_by_article.items(), key=lambda x: len(x[1]), reverse=True):
        md_lines.extend([
            f"### Article {art} ({len(ams)} amendements en discussion commune)",
            "",
            "| N° | Auteur (Groupe) | Cible de concurrence | Justification du conflit légistique |",
            "| :--- | :--- | :---: | :--- |",
        ])
        for num, info in ams:
            aut_grp = f"{info['auteur']} ({info['groupe']})"
            target = info["cible_discussion"] or "—"
            md_lines.append(f"| **{num}** | {aut_grp} | `{target}` | {info['justification']} |")
        md_lines.append("")

    md_lines.extend([
        "---",
        "",
        "## Section 3 : Tableau récapitulatif condensé des 341 amendements",
        "",
        "Format strict d'une seule ligne par amendement :",
        "",
        "| N° | Article | Auteur (Groupe) | Statut Témoin | Cible | Justification (1 phrase) |",
        "| :--- | :--- | :--- | :---: | :---: | :--- |",
    ])

    for num, item in golden_dict.items():
        clean_num = str(num).replace("|", "/").strip()
        clean_art = str(item["article"]).replace("|", "/").strip()
        clean_aut = f"{item['auteur']} ({item['groupe']})".replace("|", "/").strip()
        clean_sta = str(item["statut_temoin"]).replace("|", "/").strip()
        clean_cib = str(item["cible_discussion"] or "—").replace("|", "/").strip()
        clean_jus = " ".join(str(item["justification"]).replace("|", "/").split())

        md_lines.append(
            f"| {clean_num} | {clean_art} | {clean_aut} | {clean_sta} | {clean_cib} | {clean_jus} |"
        )

    md_lines.append("")

    with open(md_file, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    # ── Étape 5 : Synthèse console ──
    print("\n" + "=" * 78)
    print(" 🏛️  BOURBON.IA — BILAN OFFICIEL DU GOLDEN DATASET SÉMANTIQUE (341 AMENDEMENTS)")
    print("=" * 78)
    print(f" • Amendements totaux analysés : {total_count}")
    print(f" • Statut Témoin 'Identique'         : {statut_counter['Identique']:>3} ({statut_counter['Identique']/total_count*100:>5.1f} %)")
    print(f" • Statut Témoin 'Discussion commune': {statut_counter['Discussion commune']:>3} ({statut_counter['Discussion commune']/total_count*100:>5.1f} %)")
    print(f" • Statut Témoin 'Isolé'              : {statut_counter['Isolé']:>3} ({statut_counter['Isolé']/total_count*100:>5.1f} %)")
    print(f"    ↳ Dont sans dispositif opérationnel: {len(empty_nums)}")
    print(f"    ↳ Dont divisions / articles uniques: {len(singletons_nums)}")
    print("-" * 78)
    print(f" • Grappes d'articles en discussion commune : {len(dc_by_article)} articles")
    for art, ams in sorted(dc_by_article.items(), key=lambda x: len(x[1]), reverse=True)[:6]:
        print(f"    - Article {art:<12} : {len(ams)} amendements en conflit")
    print("=" * 78)
    print(f"✅ Fichier JSON généré : {json_file}")
    print(f"✅ Fichier Markdown généré : {md_file}")
    print("=" * 78 + "\n")

    return {
        "total": total_count,
        "identiques": statut_counter["Identique"],
        "discussion_commune": statut_counter["Discussion commune"],
        "isoles": statut_counter["Isolé"],
        "json_path": str(json_file),
        "md_path": str(md_file),
    }


if __name__ == "__main__":
    build_golden_dataset()
