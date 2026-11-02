#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/audit_qualification_341.py
Bourbon.ia — Lead QA & Legal Data Engineer
Audit légistique automatisé des 341 amendements de public/sample-amendments.json.

Moteurs audités :
  1. Chapeaux légistiques AN / Sénat (parse_chapeau)
  2. Dérouleur mathématique de séance (calculer_priorite_derouleur)
  3. Recevabilité financière constitutionnelle (auditer_recevabilite_art40)
  4. Dispositions non normatives / neutrons (detecter_dispositions_non_normatives)
  5. Typographie officielle JO (normaliser_typographie_jo)
  6. Tri déterministe et jumeaux (process_deterministic_sorting)
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

# Ajout de la racine du projet dans sys.path pour les imports Bourbon.ia
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from api.legal_chapeau_parser import (
    parse_chapeau,
    calculer_priorite_derouleur,
    auditer_recevabilite_art40,
    detecter_dispositions_non_normatives,
    _strip_html,
    _fingerprint_text,
    ChapeauAnalysis,
)
from api.legal_typography import normaliser_typographie_jo
from api.deputes_resolver import (
    resolve_signataires,
    get_depute_info,
    MAPPING_ORGANES_XVII,
)
from api.index import _build_enriched
from api.deterministic_engine import process_deterministic_sorting, StatutMecanique


def format_initials(full_name: str) -> str:
    """Formate les prénoms sous forme d'initiales (ex: 'Jean-François Coulomme' -> 'J.-F. Coulomme')."""
    if not full_name:
        return ""
    parts = full_name.strip().split()
    if len(parts) <= 1:
        return full_name
    first, last = parts[0], " ".join(parts[1:])
    if "-" in first:
        sub = [p[0] + "." for p in first.split("-") if p]
        first_init = "-".join(sub)
    else:
        first_init = first[0] + "."
    return f"{first_init} {last}"


def format_article_vise(division: dict[str, Any]) -> str:
    """Nettoie la désignation de l'article visé pour l'affichage concis (ex: 'PREMIER', '5', 'AVANT PREMIER')."""
    art_courte = division.get("articleDesignationCourte", "") or division.get("titre", "") or ""
    clean = re.sub(r"^(?:ARTICLE|ART\.)\s+", "", art_courte, flags=re.IGNORECASE)
    clean = re.sub(r"\bART\.\s+", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bARTICLE\s+", "", clean, flags=re.IGNORECASE)
    return clean.strip() or art_courte.strip() or "Non spécifié"


def format_action_cible(chapeau: ChapeauAnalysis, is_add: bool = False, is_empty: bool = False) -> str:
    """Formate la colonne 'Action & Cible' selon la norme parlementaire."""
    if is_empty:
        return "Sans dispositif (Retiré/Caduc)"

    v = chapeau.verbe or ("INSERER" if is_add else "NON QUALIFIE")
    c = chapeau.cible_type or ("ARTICLE" if is_add else "")

    cible_desc = ""
    if is_add:
        cible_desc = "Article additionnel"
    elif c == "ARTICLE":
        if v in ("SUPPRIMER", "REDIGER_AINSI", "RETABLIR"):
            cible_desc = "Article entier"
        elif v == "COMPLETER":
            cible_desc = "Article in fine"
        else:
            cible_desc = "Article"
    elif c == "ALINEA":
        if chapeau.alinea_fin:
            cible_desc = f"Alinéas {chapeau.alinea_num} à {chapeau.alinea_fin}"
        elif chapeau.alinea_num:
            cible_desc = f"Alinéa {chapeau.alinea_num}"
        else:
            cible_desc = "Alinéa"
    elif c == "PHRASE":
        cible_desc = f"Alinéa {chapeau.alinea_num or 1}, phrase {chapeau.rang_phrase or 1}"
    elif c == "MOTS":
        if chapeau.alinea_num:
            occ = f" ({chapeau.occurrence_mention})" if chapeau.occurrence_mention else ""
            cible_desc = f"Alinéa {chapeau.alinea_num}, mots{occ}"
        else:
            cible_desc = "Mots"
    elif c:
        cible_desc = c.capitalize()

    return f"{v} ({cible_desc})" if cible_desc else v


def resoudre_auteur_et_groupe(am: dict[str, Any]) -> tuple[str, str, str]:
    """
    Extrait et résout le nom de l'auteur principal et son groupe politique.
    Retourne (nom_complet, groupe, affichage_formate).
    """
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
    display = f"{format_initials(nom_final)} ({grp_final})" if grp_final else format_initials(nom_final)
    return (nom_final, grp_final, display)


def executer_audit() -> dict[str, Any]:
    """Exécute l'audit complet des 341 amendements et génère le rapport."""
    json_path = ROOT_DIR / "public" / "sample-amendments.json"
    if not json_path.exists():
        raise FileNotFoundError(f"Fichier de données introuvable : {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        amendements_bruts: list[dict[str, Any]] = json.load(f)

    total_count = len(amendements_bruts)

    # ── 1. Pipeline déterministe pour jumeaux & doublons ──
    enriched_list = [_build_enriched(raw, idx) for idx, raw in enumerate(amendements_bruts)]
    processed_pipeline = process_deterministic_sorting(enriched_list)

    identiques_officiels_count = sum(
        1 for a in processed_pipeline if a.statut_mecanique == StatutMecanique.IDENTIQUE_OFFICIEL
    )
    identiques_mecaniques_count = sum(
        1 for a in processed_pipeline if a.statut_mecanique == StatutMecanique.IDENTIQUE_MECANIQUE
    )
    doublons_mecaniques_count = sum(
        1 for a in processed_pipeline if a.statut_mecanique == StatutMecanique.DOUBLON_MECANIQUE
    )
    total_tri_deterministe = identiques_officiels_count + identiques_mecaniques_count + doublons_mecaniques_count

    # Détection des doublons textuels par empreinte
    fingerprints: dict[str, list[str]] = defaultdict(list)
    for a in processed_pipeline:
        if a.dispositif_clean:
            fp = _fingerprint_text(a.dispositif_clean)
            fingerprints[fp].append(a.numero_long)
    groupes_jumeaux_textuels = {k: v for k, v in fingerprints.items() if len(v) > 1}
    total_amendements_jumeaux = sum(len(v) for v in groupes_jumeaux_textuels.values())

    # ── 2. Audit individuel des 341 amendements ──
    journal_rows: list[dict[str, Any]] = []
    alertes_art40: list[dict[str, Any]] = []
    alertes_non_normatif: list[dict[str, Any]] = []
    verbes_counter: Counter[str] = Counter()
    typo_modifiees = 0

    for idx, am in enumerate(amendements_bruts):
        num = am.get("identification", {}).get("numeroLong") or am.get("numero") or f"Amdt-{idx+1}"
        division = am.get("pointeurFragmentTexte", {}).get("division", {})
        article_vise = format_article_vise(division)
        is_add = division.get("articleAdditionnel") == "true" or "additionnel" in str(division.get("type", "")).lower()

        nom_complet, grp, auteur_affiche = resoudre_auteur_et_groupe(am)

        corps = am.get("corps", {})
        contenu_auteur = corps.get("contenuAuteur", {}) if isinstance(corps, dict) else {}
        disp_raw = (
            contenu_auteur.get("dispositif")
            or (corps.get("dispositif") if isinstance(corps, dict) else "")
            or am.get("dispositif")
            or ""
        )
        disp_clean = _strip_html(disp_raw).strip()
        is_empty = not bool(disp_clean)

        desig = division.get("articleDesignation", "") or ""

        # 1. Analyse du chapeau légistique
        if is_empty:
            chapeau = parse_chapeau("")
            verbe_affiche = "Sans dispositif (Retiré/Caduc)"
        else:
            chapeau = parse_chapeau(disp_raw)
            # Repli sur articleDesignation si le chapeau est déporté dans les métadonnées AN
            if not chapeau.verbe and desig:
                chapeau = parse_chapeau(f"{desig}\n{disp_raw}")
            verbe_affiche = chapeau.verbe or ("INSERER" if is_add else "NON QUALIFIE")

        verbes_counter[verbe_affiche] += 1
        action_cible = format_action_cible(chapeau, is_add=is_add, is_empty=is_empty)

        # 2. Priorité mathématique au dérouleur
        prio_tuple = calculer_priorite_derouleur(am)
        rang_derouleur = prio_tuple[0]

        # 3. Audit constitutionnel Article 40
        audit_40 = auditer_recevabilite_art40(disp_raw, am)
        has_art40_alert = audit_40["alerte_recevabilite_art40"]
        if has_art40_alert:
            col_art40 = "Alerte (sans gage)"
            alertes_art40.append(
                {
                    "numero": num,
                    "auteur": nom_complet,
                    "groupe": grp,
                    "motif": audit_40["motif_art40"],
                    "termes": audit_40["termes_risque"],
                }
            )
        elif audit_40["gage_detecte"]:
            col_art40 = f"Conforme ({audit_40['gage_detecte']})"
        else:
            col_art40 = "Conforme"

        # 4. Détection dispositions non normatives (Art. 6 DDHC)
        audit_norm = detecter_dispositions_non_normatives(disp_raw)
        has_norm_alert = audit_norm["alerte_non_normatif"]
        if has_norm_alert:
            col_normatif = "Alerte (non normatif)"
            # Extraction propre centrée sur la formule ou texte complet sans saut de ligne
            extrait_propre = " ".join(disp_clean.split())
            if len(extrait_propre) > 350:
                extrait_propre = extrait_propre[:347] + "..."
            alertes_non_normatif.append(
                {
                    "numero": num,
                    "auteur": nom_complet,
                    "groupe": grp,
                    "formules": audit_norm["formules_detectees"],
                    "extrait": extrait_propre,
                }
            )
        else:
            col_normatif = "Normatif"

        # 5. Normalisation typographique JO
        if not is_empty:
            disp_typo = normaliser_typographie_jo(disp_clean)
            if disp_typo != disp_clean:
                typo_modifiees += 1

        journal_rows.append(
            {
                "numero": num,
                "auteur_display": auteur_affiche,
                "article_vise": article_vise,
                "action_cible": action_cible,
                "rang_derouleur": rang_derouleur,
                "art40": col_art40,
                "portee_normative": col_normatif,
            }
        )

    # ── 3. Synthèse console de la Section 1 ──
    print("\n" + "=" * 78)
    print(" 🏛️  BOURBON.IA — TABLEAU DE BORD GLOBAL DE QUALIFICATION LÉGISTIQUE (341 AMENDEMENTS)")
    print("=" * 78)
    print(f" • Amendements totaux analysés           : {total_count}")
    print(f" • Risques Article 40 détectés (sans gage): {len(alertes_art40)}")
    print(f" • Portée normative faible (Art. 6 DDHC) : {len(alertes_non_normatif)}")
    print(f" • Tri déterministe (identiques/doublons): {total_tri_deterministe} / {total_count} ({total_tri_deterministe/total_count*100:.1f} %)")
    print(f"    - Identiques officiels (champ AN)    : {identiques_officiels_count}")
    print(f"    - Identiques mécaniques (empreinte)  : {identiques_mecaniques_count}")
    print(f"    - Doublons mécaniques d'un même auteur: {doublons_mecaniques_count}")
    print(f"    - Jumeaux textuels totaux (empreinte): {total_amendements_jumeaux} amendements sur {len(groupes_jumeaux_textuels)} groupes")
    print(f" • Ajustements typographiques JO appliqués: {typo_modifiees} / {total_count - verbes_counter.get('Sans dispositif (Retiré/Caduc)', 0)}")
    print("-" * 78)
    print(" Distribution des verbes d'action du chapeau :")
    for vb, cnt in verbes_counter.most_common():
        pct = (cnt / total_count) * 100
        print(f"    - {vb:<30} : {cnt:>3} ({pct:>5.1f} %)")
    print("=" * 78 + "\n")

    # ── 4. Génération du rapport Markdown structuré ──
    reports_dir = ROOT_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / "audit_qualification_341.md"

    md_lines: list[str] = [
        "# Rapport d'Audit et de Qualification Légistique — 341 Amendements",
        "",
        "> **Bourbon.ia — Moteur d'Ingénierie Légistique et Constitutionnelle**  ",
        f"> *Source : `public/sample-amendments.json` | Volume audité : {total_count} amendements | Règlements AN & Sénat*",
        "",
        "---",
        "",
        "## Section 1 : Tableau de bord global (Métriques consolidées)",
        "",
        "| Métrique d'audit | Valeur | Proportion | Commentaire légistique |",
        "| :--- | :---: | :---: | :--- |",
        f"| **Amendements totaux analysés** | **{total_count}** | 100,0 % | Intégralité du corpus du projet de loi |",
        f"| **Alertes Article 40 (sans gage)** | **{len(alertes_art40)}** | {len(alertes_art40)/total_count*100:.1f} % | Risque d'irrecevabilité financière constitutionnelle |",
        f"| **Alertes non normatif (Art. 6 DDHC)** | **{len(alertes_non_normatif)}** | {len(alertes_non_normatif)/total_count*100:.1f} % | Neutrons législatifs dépourvus de portée contraignante |",
        f"| **Tri déterministe (identiques & doublons)** | **{total_tri_deterministe}** | {total_tri_deterministe/total_count*100:.1f} % | Traités mécaniquement à coût zéro (sans appel LLM) |",
        f"| ↳ *Identiques officiels (AN discussionIdentique)* | {identiques_officiels_count} | {identiques_officiels_count/total_count*100:.1f} % | Regroupés officiellement par les services de la séance |",
        f"| ↳ *Identiques mécaniques (empreinte texte)* | {identiques_mecaniques_count} | {identiques_mecaniques_count/total_count*100:.1f} % | Rapprochés par similarité exacte du texte dispositif |",
        f"| ↳ *Doublons mécaniques même auteur* | {doublons_mecaniques_count} | {doublons_mecaniques_count/total_count*100:.1f} % | Redéposés par le même député (à retirer) |",
        f"| **Conformité typographique JO (espaces & tirets)** | **{typo_modifiees}** | {typo_modifiees/(total_count - 45)*100:.1f} % | Normalisation stricte selon les règles du Journal Officiel |",
        "",
        "### Distribution des verbes d'action du chapeau",
        "",
        "| Verbe d'action légistique | Amendements | Part relative | Règle de recevabilité associée |",
        "| :--- | :---: | :---: | :--- |",
    ]

    regles_verbes = {
        "INSERER": "Création d'articles additionnels ou d'alinéas intercalés",
        "SUPPRIMER": "Suppression totale d'articles ou d'alinéas ciblés (priorité haute au dérouleur)",
        "SUBSTITUER": "Substitution chirurgicale de mots ou membres de phrase",
        "COMPLETER": "Adjonction in fine à la fin d'un article ou alinéa (priorité 800)",
        "REDIGER_AINSI": "Réécriture intégrale d'un article ou alinéa (priorité 20)",
        "AJOUTER": "Insertion en tête d'article ou d'alinéa (« Au début »)",
        "RETABLIR": "Rétablissement d'un article ou d'une division supprimée",
        "REMPLACER": "Remplacement d'un alinéa ou d'une division",
        "Sans dispositif (Retiré/Caduc)": "Amendements déclarés sans dispositif ou caducs avant séance",
    }

    for vb, cnt in verbes_counter.most_common():
        pct = (cnt / total_count) * 100
        desc = regles_verbes.get(vb, "Catégorie d'action légistique standard")
        md_lines.append(f"| `{vb}` | {cnt} | {pct:.1f} % | {desc} |")

    md_lines.extend(
        [
            "",
            "---",
            "",
            "## Section 2 : Top des alertes de recevabilité et constitutionnelles",
            "",
            "### 1. Alertes Article 40 de la Constitution (Diminution de recettes sans gage financier)",
            "",
            "Ces amendements introduisent des dispositions à impact financier direct (exonération, compensation, crédit d'impôt) sans inclure de formule de gage constitutionnelle valide en fin de dispositif :",
            "",
            "| N° | Auteur | Groupe | Risque et Motif d'irrecevabilité financière |",
            "| :--- | :--- | :---: | :--- |",
        ]
    )

    if alertes_art40:
        for a in alertes_art40:
            md_lines.append(f"| **{a['numero']}** | {a['auteur']} | {a['groupe']} | {a['motif']} |")
    else:
        md_lines.append("| — | Aucun risque détecté | — | Tous les amendements respectent l'Article 40 |")

    md_lines.extend(
        [
            "",
            "### 2. Alertes Dispositions Non Normatives (Neutrons législatifs - Art. 6 DDHC)",
            "",
            "Ces amendements comportent des formules déclaratives sans portée prescriptive réelle, passibles de censure par le Conseil constitutionnel (Décisions n° 2004-500 DC et 2005-512 DC) :",
            "",
            "| N° | Auteur | Groupe | Extrait non normatif relevé |",
            "| :--- | :--- | :---: | :--- |",
        ]
    )

    if alertes_non_normatif:
        for a in alertes_non_normatif:
            formules = ", ".join(f"`{f}`" for f in a["formules"])
            md_lines.append(
                f"| **{a['numero']}** | {a['auteur']} | {a['groupe']} | Formule détectée : {formules}<br>« {a['extrait']} » |"
            )
    else:
        md_lines.append("| — | Aucun neutron détecté | — | Tous les amendements disposent d'une portée normative |")

    md_lines.extend(
        [
            "",
            "---",
            "",
            "## Section 3 : Journal exhaustif de qualification (1 ligne par amendement)",
            "",
            "Format condensé strict d'une seule ligne par amendement :",
            "",
            "| N° | Auteur (Groupe) | Article visé | Action & Cible | Rang Dérouleur | Art. 40 | Portée normative |",
            "| :--- | :--- | :--- | :--- | :---: | :---: | :---: |",
        ]
    )

    for row in journal_rows:
        # Nettoyage strict pour préserver 1 seule ligne par amendement
        n_num = str(row["numero"]).replace("|", "/").strip()
        n_aut = str(row["auteur_display"]).replace("|", "/").strip()
        n_art = str(row["article_vise"]).replace("|", "/").strip()
        n_act = str(row["action_cible"]).replace("|", "/").strip()
        n_der = str(row["rang_derouleur"]).strip()
        n_a40 = str(row["art40"]).replace("|", "/").strip()
        n_nor = str(row["portee_normative"]).replace("|", "/").strip()

        md_lines.append(f"| {n_num} | {n_aut} | {n_art} | {n_act} | {n_der} | {n_a40} | {n_nor} |")

    md_lines.append("")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"✅ Rapport généré avec succès : {report_file} ({len(journal_rows)} amendements qualifiés)")

    return {
        "total": total_count,
        "alertes_art40": len(alertes_art40),
        "alertes_non_normatif": len(alertes_non_normatif),
        "tri_deterministe": total_tri_deterministe,
        "verbes": dict(verbes_counter),
        "report_file": str(report_file),
    }


if __name__ == "__main__":
    executer_audit()
