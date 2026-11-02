"""
tests/test_legal_chapeau_parser.py — Tests unitaires et d'intégration du moteur légistique AN/Sénat
===================================================================================================
Valide de manière déterministe :
  1. L'extraction des 7 verbes cardinaux d'action (AN p. 10-13, Sénat p. 32-34) et du ciblage anatomique.
  2. La règle ordinale des phrases du Sénat (p. 26 : seconde vs deuxième, règle des 5 éléments pour avant-dernière).
  3. L'ordonnancement mathématique complet au Dérouleur de séance (`calculer_priorite_derouleur`) et les identiques.
  4. L'audit constitutionnel de recevabilité financière au titre de l'Article 40 (4 gages + clause crédit d'impôt Sénat p. 65).
  5. L'intégration bout-en-bout avec `api/deterministic_engine.py` et `api/index.py`.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.legal_chapeau_parser import (
    CibleType,
    VerbeAction,
    auditer_recevabilite_art40,
    calculer_priorite_derouleur,
    ordonner_au_derouleur,
    parse_chapeau,
    qualifier_ordinal_senat,
    valider_ordinal_phrase,
)
from api.deterministic_engine import process_deterministic_sorting
from api.index import _build_enriched, _to_frontend, normaliser_amendement
from api.schemas import EnrichedAmendment


# ──────────────────────────────────────────────────────────────────────────
# 1. CHANTIER 1 : Extraction des 7 verbes d'action et ciblage anatomique
# ──────────────────────────────────────────────────────────────────────────

def test_verbe_supprimer_formulations_an_senat():
    """Teste l'extraction du verbe SUPPRIMER sur article, plage d'alinéas, fin d'alinéa et mots."""
    # Suppression d'article entier
    r1 = parse_chapeau("Supprimer cet article.")
    assert r1.verbe == VerbeAction.SUPPRIMER.value
    assert r1.cible_type == CibleType.ARTICLE.value
    assert r1.alinea_num is None

    # Suppression d'une plage d'alinéas
    r2 = parse_chapeau("Supprimer les alinéas 3 à 5.")
    assert r2.verbe == VerbeAction.SUPPRIMER.value
    assert r2.cible_type == CibleType.ALINEA.value
    assert r2.alinea_num == 3
    assert r2.alinea_fin == 5
    assert r2.alineas_vises == [3, 4, 5]

    # Suppression de fin d'alinéa après un mot
    r3 = parse_chapeau("Après le mot : « territoire », supprimer la fin de l'alinéa 4.")
    assert r3.verbe == VerbeAction.SUPPRIMER.value
    assert r3.cible_type == CibleType.ALINEA.value
    assert r3.alinea_num == 4


def test_verbe_rediger_ainsi_formulations_an_senat():
    """Teste l'extraction du verbe REDIGER_AINSI sur article entier et sur phrase d'alinéa."""
    r1 = parse_chapeau("Rédiger ainsi cet article :\n« Art. L. 121-1. – Les communes... »")
    assert r1.verbe == VerbeAction.REDIGER_AINSI.value
    assert r1.cible_type == CibleType.ARTICLE.value
    assert r1.alinea_num is None

    r2 = parse_chapeau("À l'alinéa 5, rédiger ainsi la première phrase :\n« La demande est déposée... »")
    assert r2.verbe == VerbeAction.REDIGER_AINSI.value
    assert r2.cible_type == CibleType.PHRASE.value
    assert r2.alinea_num == 5
    assert r2.rang_phrase == 1
    assert r2.ordinal_phrase == "première"


def test_verbes_remplacer_et_substituer_formulations_an_senat():
    """Teste l'extraction des verbes REMPLACER et SUBSTITUER."""
    # Sénat : Remplacer un alinéa par deux alinéas
    r1 = parse_chapeau("À l'alinéa 2, remplacer cet alinéa par deux alinéas ainsi rédigés :\n« 1° ... »")
    assert r1.verbe == VerbeAction.REMPLACER.value
    assert r1.cible_type == CibleType.ALINEA.value
    assert r1.alinea_num == 2

    # AN : Substituer aux mots
    r2 = parse_chapeau("À l'alinéa 3, substituer au mot : « trois » les mots : « au moins quatre ».")
    assert r2.verbe == VerbeAction.SUBSTITUER.value
    assert r2.cible_type == CibleType.MOTS.value
    assert r2.alinea_num == 3


def test_verbe_inserer_formulations_an_senat():
    """Teste l'extraction du verbe INSERER (adjonction intercalaire d'alinéa ou de mots)."""
    r1 = parse_chapeau("Après l'alinéa 4, insérer l'alinéa suivant :\n« Le décret précise ces modalités. »")
    assert r1.verbe == VerbeAction.INSERER.value
    assert r1.cible_type == CibleType.ALINEA.value
    assert r1.alinea_num == 4

    r2 = parse_chapeau("À l'alinéa 2, après le mot : « préfet », insérer les mots : « de région ».")
    assert r2.verbe == VerbeAction.INSERER.value
    assert r2.cible_type == CibleType.MOTS.value
    assert r2.alinea_num == 2


def test_verbe_ajouter_formulations_an_senat():
    """Teste l'extraction du verbe AJOUTER (adjonction en tête d'article ou d'alinéa)."""
    r1 = parse_chapeau("Au début, ajouter les deux alinéas suivants :\n« I A. – ... »")
    assert r1.verbe == VerbeAction.AJOUTER.value
    assert r1.cible_type == CibleType.ALINEA.value
    assert r1.alinea_num is None

    r2 = parse_chapeau("Au début de l'alinéa 1, ajouter la phrase suivante :\n« Par dérogation, ... »")
    assert r2.verbe == VerbeAction.AJOUTER.value
    assert r2.cible_type == CibleType.PHRASE.value
    assert r2.alinea_num == 1


def test_verbe_completer_formulations_an_senat():
    """Teste l'extraction du verbe COMPLETER (adjonction in fine d'article ou d'alinéa)."""
    r1 = parse_chapeau("Compléter cet article par les mots : « dans un délai de six mois ».")
    assert r1.verbe == VerbeAction.COMPLETER.value
    assert r1.cible_type == CibleType.ARTICLE.value
    assert r1.alinea_num is None

    r2 = parse_chapeau("Compléter l'alinéa 4 par la phrase suivante :\n« Un arrêté fixe le barème. »")
    assert r2.verbe == VerbeAction.COMPLETER.value
    assert r2.cible_type == CibleType.PHRASE.value
    assert r2.alinea_num == 4


def test_verbe_retablir_formulations_an_senat():
    """Teste l'extraction du verbe RETABLIR (article ou subdivision supprimé lors d'une lecture précédente)."""
    r1 = parse_chapeau("Rétablir cet article dans la rédaction suivante :\n« Le I de l'article... »")
    assert r1.verbe == VerbeAction.RETABLIR.value
    assert r1.cible_type == CibleType.ARTICLE.value
    assert r1.alinea_num is None

    r2 = parse_chapeau("À l'alinéa 6, rétablir le IV dans la rédaction suivante :\n« IV. – ... »")
    assert r2.verbe == VerbeAction.RETABLIR.value
    assert r2.cible_type == CibleType.ALINEA.value
    assert r2.alinea_num == 6


def test_cibles_anatomiques_specifiques_et_occurrences():
    """Teste les cibles DIVISION, INTITULE, TABLEAU, ANNEXE et les occurrences multiples de mots."""
    # DIVISION
    r_div = parse_chapeau("Supprimer cette division et son intitulé.")
    assert r_div.verbe == VerbeAction.SUPPRIMER.value
    assert r_div.cible_type in (CibleType.INTITULE.value, CibleType.DIVISION.value)

    r_div2 = parse_chapeau("Rétablir cette division dans la rédaction suivante :")
    assert r_div2.verbe == VerbeAction.RETABLIR.value
    assert r_div2.cible_type == CibleType.DIVISION.value

    # INTITULE
    r_int = parse_chapeau("Rédiger ainsi l'intitulé de cet article :")
    assert r_int.verbe == VerbeAction.REDIGER_AINSI.value
    assert r_int.cible_type == CibleType.INTITULE.value

    # TABLEAU
    r_tab = parse_chapeau("À l'alinéa 3, remplacer la deuxième colonne du tableau par la colonne suivante :")
    assert r_tab.verbe == VerbeAction.REMPLACER.value
    assert r_tab.cible_type == CibleType.TABLEAU.value
    assert r_tab.alinea_num == 3

    # ANNEXE
    r_ann = parse_chapeau("Compléter l'annexe par un alinéa ainsi rédigé :")
    assert r_ann.verbe == VerbeAction.COMPLETER.value
    assert r_ann.cible_type == CibleType.ANNEXE.value

    # OCCURRENCES MULTIPLES (« supprimer (trois fois) le mot X », « supprimer la seconde occurrence du mot Y »)
    r_occ1 = parse_chapeau("À l'alinéa 2, supprimer (trois fois) le mot : « provisoire ».")
    assert r_occ1.verbe == VerbeAction.SUPPRIMER.value
    assert r_occ1.cible_type == CibleType.MOTS.value
    assert r_occ1.occurrence_mots == 3
    assert r_occ1.occurrence_mention == "trois fois"

    r_occ2 = parse_chapeau("À l'alinéa 7, supprimer la seconde occurrence du mot : « notamment ».")
    assert r_occ2.verbe == VerbeAction.SUPPRIMER.value
    assert r_occ2.cible_type == CibleType.MOTS.value
    assert r_occ2.occurrence_mots == 2
    assert r_occ2.occurrence_mention == "seconde occurrence"


# ──────────────────────────────────────────────────────────────────────────
# 2. Règle ordinale des phrases (Sénat p. 26)
# ──────────────────────────────────────────────────────────────────────────

def test_regle_ordinale_phrases_senat_p26():
    """
    Valide la règle ordinale stricte du Sénat (p. 26) :
      - « seconde » uniquement si l'élément n'a que 2 composants ;
      - « deuxième », « troisième » si >= 3 composants ;
      - « avant-dernière » uniquement recevable si l'élément comporte au moins 5 composants.
    """
    # 1. Élément à 2 composants : « seconde » obligatoire, « deuxième » irrecevable
    assert qualifier_ordinal_senat(2, 2, feminin=True) == "seconde"
    v_sec_2 = valider_ordinal_phrase("seconde", nb_composants=2)
    assert v_sec_2["recevable"] is True
    assert v_sec_2["ordinal_normalise"] == "seconde"

    v_deux_2 = valider_ordinal_phrase("deuxième", nb_composants=2)
    assert v_deux_2["recevable"] is False
    assert v_deux_2["ordinal_normalise"] == "seconde"
    assert "seconde" in v_deux_2["motif"]

    # 2. Élément à 3 ou 4 composants : « deuxième » recevable, « seconde » irrecevable
    assert qualifier_ordinal_senat(2, 3, feminin=True) == "deuxième"
    assert qualifier_ordinal_senat(3, 4, feminin=True) == "troisième"
    v_sec_3 = valider_ordinal_phrase("seconde", nb_composants=3)
    assert v_sec_3["recevable"] is False
    assert v_sec_3["ordinal_normalise"] == "deuxième"

    v_deux_3 = valider_ordinal_phrase("deuxième", nb_composants=3)
    assert v_deux_3["recevable"] is True
    assert v_deux_3["ordinal_normalise"] == "deuxième"

    # 3. Règle des 5 éléments pour « avant-dernière »
    # Avec 4 composants : le 3e est « troisième » et NON « avant-dernière »
    v_av_4 = valider_ordinal_phrase("avant-dernière", nb_composants=4)
    assert v_av_4["recevable"] is False
    assert v_av_4["ordinal_normalise"] == "troisième"
    assert "5 composants" in v_av_4["motif"]

    # Avec 5 composants : le 4e est bien « avant-dernière »
    assert qualifier_ordinal_senat(4, 5, feminin=True) == "avant-dernière"
    v_av_5 = valider_ordinal_phrase("avant-dernière", nb_composants=5)
    assert v_av_5["recevable"] is True
    assert v_av_5["ordinal_normalise"] == "avant-dernière"
    assert v_av_5["rang_numerique"] == 4

    # Vérification via parse_chapeau avec nb_composants
    ch_irrecevable = parse_chapeau(
        "À l'alinéa 3, supprimer l'avant-dernière phrase.", nb_composants=4
    )
    assert ch_irrecevable.ordinal_recevable is False
    assert ch_irrecevable.ordinal_phrase == "troisième"

    ch_recevable = parse_chapeau(
        "À l'alinéa 3, supprimer l'avant-dernière phrase.", nb_composants=5
    )
    assert ch_recevable.ordinal_recevable is True
    assert ch_recevable.ordinal_phrase == "avant-dernière"


# ──────────────────────────────────────────────────────────────────────────
# 3. CHANTIER 2 : Calculateur d'ordre au Dérouleur de séance
# ──────────────────────────────────────────────────────────────────────────

def test_ordonnancement_complet_derouleur():
    """
    Valide l'ordonnancement mathématique complet au Dérouleur de séance :
    Suppression (10) < Rédaction globale (20) < Alinéa 1 Phrase 1 (41) < Alinéa 1 Phrase 2 (42)
    < Alinéa 2 (50) < Compléter in fine (800) < Article additionnel (900).
    """
    am_additionnel = {
        "id": "AM-ADD-900",
        "article": "APRÈS L'ARTICLE 1ER",
        "dispositif": "Après l'article 1er, insérer l'article suivant : « Art. 1er bis. – ... »",
    }
    am_completer = {
        "id": "AM-COMP-800",
        "article": "Article 1er",
        "dispositif": "Compléter cet article par l'alinéa suivant : « III. – Un décret... »",
    }
    am_alinea_2 = {
        "id": "AM-AL2-50",
        "article": "Article 1er",
        "dispositif": "Supprimer l'alinéa 2.",
    }
    am_alinea_1_phrase_2 = {
        "id": "AM-AL1-P2-42",
        "article": "Article 1er",
        "dispositif": "À l'alinéa 1, supprimer la seconde phrase.",
    }
    am_alinea_1_phrase_1 = {
        "id": "AM-AL1-P1-41",
        "article": "Article 1er",
        "dispositif": "À l'alinéa 1, rédiger ainsi la première phrase : « L'État garantit... »",
    }
    am_alinea_1_entier = {
        "id": "AM-AL1-40",
        "article": "Article 1er",
        "dispositif": "Supprimer l'alinéa 1.",
    }
    am_redaction_globale = {
        "id": "AM-RED-20",
        "article": "Article 1er",
        "dispositif": "Rédiger ainsi cet article : « Le présent article... »",
    }
    am_suppression = {
        "id": "AM-SUP-10",
        "article": "Article 1er",
        "dispositif": "Supprimer cet article.",
    }

    # Vérification unitaire des priorités numériques exactes
    assert calculer_priorite_derouleur(am_suppression)[0] == 10
    assert calculer_priorite_derouleur(am_redaction_globale)[0] == 20
    assert calculer_priorite_derouleur(am_alinea_1_entier)[0] == 40          # 30 + (1 * 10) + 0
    assert calculer_priorite_derouleur(am_alinea_1_phrase_1)[0] == 41        # 30 + (1 * 10) + 1
    assert calculer_priorite_derouleur(am_alinea_1_phrase_2)[0] == 42        # 30 + (1 * 10) + 2
    assert calculer_priorite_derouleur(am_alinea_2)[0] == 50                 # 30 + (2 * 10) + 0
    assert calculer_priorite_derouleur(am_completer)[0] == 800
    assert calculer_priorite_derouleur(am_additionnel)[0] == 900

    # Mélange en ordre inversé et vérification du tri au dérouleur
    lot_desordre = [
        am_additionnel,
        am_completer,
        am_alinea_2,
        am_alinea_1_phrase_2,
        am_alinea_1_phrase_1,
        am_alinea_1_entier,
        am_redaction_globale,
        am_suppression,
    ]
    ordonnes = ordonner_au_derouleur(lot_desordre)
    ids_ordonnes = [x["amendement"]["id"] for x in ordonnes]

    assert ids_ordonnes == [
        "AM-SUP-10",
        "AM-RED-20",
        "AM-AL1-40",
        "AM-AL1-P1-41",
        "AM-AL1-P2-42",
        "AM-AL2-50",
        "AM-COMP-800",
        "AM-ADD-900",
    ]


def test_derouleur_identiques_meme_rang_appel():
    """
    Vérifie qu'à priorité égale, deux amendements ayant un texte identique
    partagent exactement le même tuple de priorité et le même rang d'appel.
    """
    am_sup_a = {"id": "AM-1", "article": "Article 3", "dispositif": "<p>Supprimer cet article.</p>"}
    am_sup_b = {"id": "AM-2", "article": "Article 3", "dispositif": "Supprimer cet article."}
    am_al1 = {"id": "AM-3", "article": "Article 3", "dispositif": "Supprimer l'alinéa 1."}

    assert calculer_priorite_derouleur(am_sup_a) == calculer_priorite_derouleur(am_sup_b)

    ordonnes = ordonner_au_derouleur([am_al1, am_sup_a, am_sup_b])
    assert ordonnes[0]["amendement"]["id"] == "AM-1"
    assert ordonnes[1]["amendement"]["id"] == "AM-2"
    assert ordonnes[0]["rang_appel"] == 1
    assert ordonnes[1]["rang_appel"] == 1
    assert ordonnes[2]["amendement"]["id"] == "AM-3"
    assert ordonnes[2]["rang_appel"] == 2


# ──────────────────────────────────────────────────────────────────────────
# 4. CHANTIER 3 : Auditeur constitutionnel de gage (Article 40)
# ──────────────────────────────────────────────────────────────────────────

def test_quatre_types_gages_constitutionnels_valides():
    """Valide la détection des 4 types de gages officiels (Tabac CGI/CIBS, Alcool, DGF, Sécurité sociale)."""
    # 1a. Gage Tabac (État) — formulation CGI art. 575 et 575 A
    disp_tabac_cgi = (
        "I. – À l'alinéa 2, le taux réduit de 5,5 % s'applique aux opérations visées.\n"
        "II. – La perte de recettes pour l'État est compensée à due concurrence par la création "
        "d'une taxe additionnelle aux droits prévus aux articles 575 et 575 A du code général des impôts."
    )
    res_tabac_cgi = auditer_recevabilite_art40(disp_tabac_cgi)
    assert res_tabac_cgi["alerte_recevabilite_art40"] is False
    assert res_tabac_cgi["gage_detecte"] == "Gage Tabac (État)"
    assert res_tabac_cgi["motif_art40"] is None

    # 1b. Gage Tabac (État) — formulation CIBS livre III titre Ier chapitre IV
    disp_tabac_cibs = (
        "I. – Il est institué un abattement de 30 % sur l'assiette imposable.\n"
        "II. – La perte de recettes résultant pour l'État du I est compensée, à due concurrence, "
        "par la création d'une taxe additionnelle à l'accise sur les tabacs prévue au chapitre IV "
        "du titre Ier du livre III du code des impositions sur les biens et services."
    )
    res_tabac_cibs = auditer_recevabilite_art40(disp_tabac_cibs)
    assert res_tabac_cibs["alerte_recevabilite_art40"] is False
    assert res_tabac_cibs["gage_detecte"] == "Gage Tabac (État)"

    # 2. Gage Alcool (État) — CGI art. 403
    disp_alcool = (
        "I. – L'exonération est prolongée jusqu'au 31 décembre 2027.\n"
        "II. – Pour compenser la perte de recettes résultant du I, compléter cet article par "
        "un paragraphe ainsi rédigé : La perte de recettes résultant pour l'État est compensée "
        "par la création d'une taxe additionnelle au droit prévu à l'article 403 du code général des impôts."
    )
    res_alcool = auditer_recevabilite_art40(disp_alcool)
    assert res_alcool["alerte_recevabilite_art40"] is False
    assert res_alcool["gage_detecte"] == "Gage Alcool (État)"

    # 3. Gage Collectivités territoriales (DGF) + État
    disp_dgf = (
        "I. – Les collectivités accordent une exonération de taxe foncière.\n"
        "II. – La perte de recettes résultant pour les collectivités territoriales est compensée, "
        "à due concurrence, par une majoration à due concurrence de la dotation globale de fonctionnement (DGF)."
    )
    res_dgf = auditer_recevabilite_art40(disp_dgf)
    assert res_dgf["alerte_recevabilite_art40"] is False
    assert res_dgf["gage_detecte"] == "Gage Collectivités territoriales (DGF)"

    # 4. Gage Sécurité sociale — CSS art. L. 136-7-1
    disp_secu = (
        "I. – Les employeurs bénéficient d'une exonération de cotisations sociales.\n"
        "II. – La perte de recettes résultant pour les organismes de sécurité sociale est compensée, "
        "à due concurrence, par la création d'une contribution additionnelle à la contribution prévue "
        "à l'article L. 136-7-1 du code de la sécurité sociale."
    )
    res_secu = auditer_recevabilite_art40(disp_secu)
    assert res_secu["alerte_recevabilite_art40"] is False
    assert res_secu["gage_detecte"] == "Gage Sécurité sociale"


def test_alerte_credit_impot_non_gage_et_regle_senat_p65():
    """
    Valide :
      1. L'alerte d'irrecevabilité Art. 40 sur un crédit d'impôt non gagé ;
      2. L'alerte sur un crédit d'impôt gagé mais omettant la clause impérative Sénat p. 65 ;
      3. La conformité d'un crédit d'impôt comportant à la fois la clause « ne s'applique qu'aux
         sommes venant en déduction de l'impôt dû » et le Gage Tabac.
    """
    # 1. Crédit d'impôt sans aucun gage -> Alerte Art. 40
    disp_ci_sans_gage = (
        "Après l'alinéa 3, insérer l'alinéa suivant :\n"
        "« Les entreprises bénéficient d'un crédit d'impôt égal à 25 % des dépenses engagées. »"
    )
    res_sans = auditer_recevabilite_art40(disp_ci_sans_gage)
    assert res_sans["alerte_recevabilite_art40"] is True
    assert res_sans["gage_detecte"] is None
    assert "crédit d'impôt" in res_sans["motif_art40"]
    assert "ne s'applique qu'aux sommes venant en déduction de l'impôt dû" in res_sans["motif_art40"]

    # 2. Crédit d'impôt avec Gage Tabac mais SANS la clause impérative Sénat p. 65 -> Alerte Art. 40
    disp_ci_sans_clause = (
        "I. – Le taux du crédit d'impôt est porté à 40 %.\n"
        "II. – La perte de recettes pour l'État est compensée par la création d'une taxe additionnelle "
        "aux droits prévus aux articles 575 et 575 A du code général des impôts."
    )
    res_sans_clause = auditer_recevabilite_art40(disp_ci_sans_clause)
    assert res_sans_clause["alerte_recevabilite_art40"] is True
    assert res_sans_clause["gage_detecte"] == "Gage Tabac (État)"
    assert "ne s'applique qu'aux sommes venant en déduction de l'impôt dû" in res_sans_clause["motif_art40"]

    # 3. Crédit d'impôt complet conforme Sénat p. 65 (Clause déduction impôt dû + Gage Tabac CIBS)
    disp_ci_conforme = (
        "I. – À l'alinéa 4, remplacer le taux : « 15 % » par le taux : « 30 % » pour ce crédit d'impôt.\n"
        "II. – Le I ne s'applique qu'aux sommes venant en déduction de l'impôt dû.\n"
        "III. – La perte de recettes résultant pour l'État du I est compensée, à due concurrence, "
        "par la création d'une taxe additionnelle à l'accise sur les tabacs prévue au chapitre IV "
        "du titre Ier du livre III du code des impositions sur les biens et services."
    )
    res_conforme = auditer_recevabilite_art40(disp_ci_conforme)
    assert res_conforme["alerte_recevabilite_art40"] is False
    assert res_conforme["gage_detecte"] == "Gage Tabac (État)"
    assert res_conforme["clause_credit_impot_presente"] is True
    assert res_conforme["motif_art40"] is None


def test_integration_pipeline_enrichissement_et_frontend():
    """Vérifie que les champs Art. 40 et Chapeau sont bien injectés dans EnrichedAmendment et _to_frontend."""
    raw_amend = {
        "uid": "AMDT-ART40-TEST",
        "numero": "404",
        "article": "Article 5",
        "dispositif": "<p>À l'alinéa 2, prévoir une exonération totale de cotisations et une prise en charge par l'État.</p>",
    }

    # Via normaliser_amendement
    norm = normaliser_amendement(dict(raw_amend), 0)
    assert norm["alerte_recevabilite_art40"] is True
    assert norm["gage_detecte"] is None
    assert "Article 40" in norm["motif_art40"]
    assert norm["alinea_num"] == 2

    # Via _build_enriched -> process_deterministic_sorting -> _to_frontend
    enriched = _build_enriched(raw_amend, 0)
    sorted_list = process_deterministic_sorting([enriched])
    front = _to_frontend(sorted_list[0])

    assert front["alerte_recevabilite_art40"] is True
    assert front["gage_detecte"] is None
    assert "exonération" in front["motif_art40"]
    assert "prise en charge par l'État" in front["motif_art40"]
    assert front["alinea_num"] == 2
    assert front["priorite_derouleur"] == 50
