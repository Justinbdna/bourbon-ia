r"""
api/export_rtf.py — Générateur d'export Préjaune parlementaire (RTF officiel de séance)
========================================================================================
Génère le document RTF de dérouleur de séance (« Préjaune ») :
  1. Ordonné strictement selon l'ordre calculé par `ordonner_au_derouleur` (Partie 1).
  2. Affichant pour chaque bloc d'amendement :
     - L'en-tête officiel : Numéro d'amendement, Auteur(s), Groupe politique, Article visé, Priorité d'appel.
     - Le statut de tri : `Identique` (avec liste des amendements jumeaux), `Discussion commune`, `Isolé`.
     - Le chapeau extrait et la cible légistique (ex: `SUPPRIMER sur Alinéa 3`).
     - Le texte du dispositif normalisé selon la Charte JO (`normaliser_typographie_jo`, espaces insécables `\~`).
     - Les alertes juridiques en marge (Article 40 ou Défaut de portée normative Art. 6 DDHC).
     - L'exposé sommaire de l'amendement.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

try:
    from api.legal_chapeau_parser import (
        auditer_recevabilite_art40,
        detecter_dispositions_non_normatives,
        ordonner_au_derouleur,
        parse_chapeau,
    )
    from api.legal_typography import NBSP, normaliser_typographie_jo
except ModuleNotFoundError:
    from legal_chapeau_parser import (  # type: ignore
        auditer_recevabilite_art40,
        detecter_dispositions_non_normatives,
        ordonner_au_derouleur,
        parse_chapeau,
    )
    from legal_typography import NBSP, normaliser_typographie_jo  # type: ignore


def rtf_escape(texte: Any) -> str:
    """
    Encode une chaîne Unicode en séquence RTF 1.9.1 valide :
      - Échappe les caractères de contrôle RTF (`\\`, `{`, `}`).
      - Convertit l'espace insécable Unicode (`\\u00A0`) en espace insécable RTF (`\\~`).
      - Convertit les retours à la ligne en `\\line `.
      - Encode les caractères non-ASCII (> 127) en `\\uNNNN?`.
    """
    if texte is None:
        return ""
    out: list[str] = []
    for ch in str(texte):
        if ch == "\\":
            out.append("\\\\")
        elif ch == "{":
            out.append("\\{")
        elif ch == "}":
            out.append("\\}")
        elif ch == NBSP:
            out.append("\\~")
        elif ch == "\n":
            out.append("\\line ")
        elif ch == "\r":
            continue
        else:
            code = ord(ch)
            if code < 128:
                out.append(ch)
            else:
                signed = code - 65536 if code > 32767 else code
                out.append(f"\\u{signed}?")
    return "".join(out)


def _extraire_champ(am: Any, *cles: str, default: Any = "") -> Any:
    """Extrait le premier champ non vide depuis un dict (éventuellement imbriqué sous 'amendement') ou un objet."""
    if isinstance(am, dict):
        inner = am.get("amendement") if isinstance(am.get("amendement"), dict) else {}
        for c in cles:
            val = am.get(c)
            if val is not None and val != "":
                return val
            val_in = inner.get(c)
            if val_in is not None and val_in != "":
                return val_in
        return default
    for c in cles:
        val = getattr(am, c, None)
        if val is not None and val != "":
            return val
    return default


def _extraire_numero(am: Any, fallback_idx: int) -> str:
    if isinstance(am, str):
        return str(fallback_idx)
    num = _extraire_champ(am, "numero", "numero_long", "numeroLong", "id", "uid", "amendement_uid")
    if not num and isinstance(am, dict):
        ident = am.get("identification") or am.get("amendement", {}).get("identification") or {}
        if isinstance(ident, dict):
            num = ident.get("numeroLong") or ident.get("numero")
    return str(num).strip() if num else str(fallback_idx)


def _extraire_auteurs(am: Any) -> str:
    if isinstance(am, str):
        return "La commission"
    auteurs = _extraire_champ(am, "auteurs", "auteurs_raw", "auteur_string")
    if isinstance(auteurs, list) and auteurs:
        propres = [str(x).strip() for x in auteurs if x and str(x).strip()]
        if propres:
            return ", ".join(propres)
    if isinstance(auteurs, str) and auteurs.strip():
        return auteurs.strip()

    auteur = _extraire_champ(am, "auteur")
    if isinstance(auteur, dict):
        nom_complet = f"{auteur.get('prenom', '')} {auteur.get('nom', '')}".strip()
        if nom_complet:
            return nom_complet
    elif isinstance(auteur, str) and auteur.strip():
        return auteur.strip()

    prenom = str(_extraire_champ(am, "auteur_prenom", default="")).strip()
    nom = str(_extraire_champ(am, "auteur_nom", default="")).strip()
    if prenom or nom:
        return f"{prenom} {nom}".strip()

    return "La commission"


def _extraire_groupe(am: Any) -> str:
    if isinstance(am, str):
        return "—"
    grp = _extraire_champ(am, "groupe_politique", "groupe", "groupRef", "groupe_politique_ref")
    if isinstance(grp, dict):
        return str(grp.get("nom") or grp.get("libelle") or grp.get("type") or "—")
    return str(grp).strip() if grp else "—"


def _extraire_article(am: Any) -> str:
    if isinstance(am, str):
        return "Article 1er"
    art = _extraire_champ(am, "article_vise", "article")
    if not art and isinstance(am, dict):
        div = (
            am.get("pointeurFragmentTexte", {}).get("division", {})
            or am.get("amendement", {}).get("pointeurFragmentTexte", {}).get("division", {})
        )
        if isinstance(div, dict):
            art = div.get("articleDesignationCourte") or div.get("titre")
    art_str = str(art).strip() if art else "Article 1er"
    return normaliser_typographie_jo(art_str)


def _extraire_dispositif(am: Any) -> str:
    if isinstance(am, str):
        return am
    disp = _extraire_champ(am, "dispositif_raw", "dispositif", "texte", "dispositif_clean")
    if not disp and isinstance(am, dict):
        corps = am.get("corps") or am.get("amendement", {}).get("corps") or {}
        if isinstance(corps, dict):
            ca = corps.get("contenuAuteur") if isinstance(corps.get("contenuAuteur"), dict) else {}
            disp = ca.get("dispositif") or corps.get("dispositif") or ""
    return str(disp).strip() if disp else ""


def _extraire_expose(am: Any) -> str:
    if isinstance(am, str):
        return ""
    exp = _extraire_champ(am, "expose_sommaire", "exposeSommaire")
    if not exp and isinstance(am, dict):
        corps = am.get("corps") or am.get("amendement", {}).get("corps") or {}
        if isinstance(corps, dict):
            ca = corps.get("contenuAuteur") if isinstance(corps.get("contenuAuteur"), dict) else {}
            exp = ca.get("exposeSommaire") or corps.get("exposeSommaire") or ""
    return str(exp).strip() if exp else ""


def _formater_cible_legistique(chapeau_info: Any) -> str:
    """Construit le libellé lisible de la cible légistique (ex: 'SUPPRIMER sur Alinéa 3')."""
    verbe = chapeau_info.verbe_action or "MODIFIER"
    cible = chapeau_info.cible_type or "ARTICLE"
    alinea_num = chapeau_info.alinea_num
    rang_phrase = chapeau_info.rang_phrase

    if alinea_num is not None and rang_phrase is not None:
        cible_str = f"Alinéa {alinea_num} (Phrase {rang_phrase})"
    elif alinea_num is not None:
        cible_str = f"Alinéa {alinea_num}"
    elif cible == "ARTICLE":
        cible_str = "Article"
    elif cible == "PHRASE" and rang_phrase is not None:
        cible_str = f"Phrase {rang_phrase}"
    else:
        cible_str = cible.capitalize()

    return f"{verbe} sur {cible_str}"


def generer_prejaune_rtf(
    amendements: list[Any],
    titre_texte: Optional[str] = None,
) -> str:
    """
    Génère le document RTF officiel de séance (« Préjaune ») :
      - Strictement ordonné selon `ordonner_au_derouleur`.
      - En-tête officiel, statut de tri (Identique + jumeaux, Discussion commune, Isolé),
        chapeau et cible légistique, dispositif normalisé JO DILA, alertes juridiques
        en marge (Article 40 et Portée normative Art. 6 DDHC), et exposé sommaire.
    """
    items_ordonnes = ordonner_au_derouleur(amendements or [])

    # Pré-calcul des numéros et regroupements (Identiques et Discussions communes)
    numeros_par_pos: list[str] = []
    groupes_empreinte: dict[tuple, list[str]] = {}
    groupes_zone_cible: dict[tuple, list[str]] = {}

    for pos, item in enumerate(items_ordonnes, start=1):
        am = item["amendement"]
        num = _extraire_numero(am, pos)
        numeros_par_pos.append(num)
        cle = item["priorite_tuple"]
        empreinte = cle[4]
        if empreinte:
            groupes_empreinte.setdefault(cle, []).append(num)
        zone_key = (cle[0], cle[1])
        groupes_zone_cible.setdefault(zone_key, []).append(num)

    lines: list[str] = [
        r"{\rtf1\ansi\ansicpg1252\deff0",
        r"{\fonttbl{\f0\froman\fcharset0 Times New Roman;}{\f1\fswiss\fcharset0 Arial;}}",
        r"{\colortbl;\red0\green0\blue0;\red180\green20\blue20;\red15\green80\blue150;\red90\green90\blue90;}",
        r"\paperw11907\paperh16840\margl1418\margr1418\margt1134\margb1134",
        r"\pard\qc\f0\fs28\b ASSEMBL\u201?E NATIONALE \emdash  PR\u201?JAUNE DE S\u201?ANCE\b0\par",
        (
            r"\pard\qc\f0\fs18\i D\u233?rouleur officiel ordonn\u233? selon la l\u233?gistique formelle "
            rf"(DILA / SGG) \emdash  G\u233?n\u233?r\u233? le {datetime.now().strftime('%d/%m/%Y')}\i0\par\par"
        ),
    ]

    if titre_texte:
        lines.append(rf"\pard\qc\f0\fs24\b\ul {rtf_escape(normaliser_typographie_jo(titre_texte))}\b0\ul0\par\par")

    for pos, item in enumerate(items_ordonnes):
        am = item["amendement"]
        num = numeros_par_pos[pos]
        priorite = item["priorite"]
        rang_appel = item["rang_appel"]
        cle = item["priorite_tuple"]

        auteurs = _extraire_auteurs(am)
        groupe = _extraire_groupe(am)
        article = _extraire_article(am)
        dispositif_brut = _extraire_dispositif(am)
        expose_brut = _extraire_expose(am)

        # Analyse légistique du chapeau et audits juridiques
        chapeau_info = parse_chapeau(dispositif_brut)
        cible_resume = _formater_cible_legistique(chapeau_info)
        chapeau_extrait = chapeau_info.chapeau_brut or "—"

        audit_40 = auditer_recevabilite_art40(dispositif_brut, am if isinstance(am, dict) else None)
        alerte_art40 = bool(
            _extraire_champ(am, "alerte_recevabilite_art40", default=False)
            or audit_40["alerte_recevabilite_art40"]
        )
        motif_art40 = (
            _extraire_champ(am, "motif_art40", default=None)
            or audit_40["motif_art40"]
            or "Risque d'irrecevabilité financière au titre de l'Article 40 de la Constitution."
        )

        audit_norm = detecter_dispositions_non_normatives(dispositif_brut)
        alerte_non_norm = bool(
            _extraire_champ(am, "alerte_non_normatif", default=False)
            or audit_norm["alerte_non_normatif"]
        )
        motif_non_norm = (
            _extraire_champ(am, "motif_non_normatif", default=None)
            or audit_norm["motif_non_normatif"]
            or "Dispositif à faible portée normative (risque de censure pour défaut de normativité, Art. 6 DDHC)."
        )

        # Détermination du statut de tri (Identique + jumeaux / Discussion commune / Isolé)
        statut_explicite = str(
            _extraire_champ(am, "statut", default="")
            or (am.get("resultat_ia", {}).get("statut") if isinstance(am, dict) and isinstance(am.get("resultat_ia"), dict) else "")
            or _extraire_champ(am, "statut_mecanique", default="")
        )
        jumeaux_groupe = [n for n in groupes_empreinte.get(cle, []) if n != num]
        jumeaux_explicites = _extraire_champ(am, "jumeaux", "amendements_jumeaux", default=[])
        if isinstance(jumeaux_explicites, list):
            for j_num in jumeaux_explicites:
                if str(j_num) not in jumeaux_groupe and str(j_num) != num:
                    jumeaux_groupe.append(str(j_num))

        if jumeaux_groupe or "identique" in statut_explicite.lower():
            if jumeaux_groupe:
                liste_jumeaux = ", ".join(f"n°{NBSP}{j}" for j in jumeaux_groupe)
                statut_tri_str = f"Identique (amendements jumeaux : {liste_jumeaux})"
            else:
                statut_tri_str = "Identique"
        elif "discussion commune" in statut_explicite.lower() or len(groupes_zone_cible.get((cle[0], cle[1]), [])) > 1:
            statut_tri_str = "Discussion commune"
        else:
            statut_tri_str = "Isolé"

        # Normalisation typographique DILA (Charte JO) du dispositif et de l'exposé sommaire
        dispositif_normalise = normaliser_typographie_jo(dispositif_brut)
        expose_normalise = normaliser_typographie_jo(expose_brut) if expose_brut else "Néant."

        # ── Construction du bloc RTF de l'amendement ──
        lines.append(r"\pard\sa120\sb180\brdrt\brdrs\brdrw15\brsp80\f0\fs22")

        # 1. En-tête officiel
        entete = (
            f"Amendement n°{NBSP}{num} | {article} | "
            f"Auteur(s){NBSP}: {auteurs} ({groupe}) | "
            f"Priorité d'appel{NBSP}: {priorite} (Rang{NBSP}{rang_appel})"
        )
        lines.append(rf"\pard\f0\fs22\b {rtf_escape(entete)}\b0\par")

        # 2. Statut de tri
        lines.append(rf"\pard\f0\fs20\b Statut de tri\~:\b0  {rtf_escape(statut_tri_str)}\par")

        # 3. Chapeau extrait et cible légistique
        lines.append(
            rf"\pard\f0\fs20\b Cible l\u233?gistique\~:\b0  {rtf_escape(cible_resume)} "
            rf"(\i Chapeau\~: {rtf_escape(normaliser_typographie_jo(chapeau_extrait))}\i0)\par"
        )

        # 4. Alertes juridiques en marge (Article 40 / Portée normative Art. 6 DDHC)
        if alerte_art40:
            lines.append(
                rf"\pard\li360\f0\fs20\cf2\b [ALERTE MARGE \emdash  ARTICLE 40]\~:\b0  "
                rf"{rtf_escape(normaliser_typographie_jo(motif_art40))}\cf1\par"
            )
        if alerte_non_norm:
            lines.append(
                rf"\pard\li360\f0\fs20\cf3\b [ALERTE MARGE \emdash  PORT\u201?E NORMATIVE FAIBLE (Art. 6 DDHC)]\~:\b0  "
                rf"{rtf_escape(normaliser_typographie_jo(motif_non_norm))}\cf1\par"
            )

        # 5. Dispositif normalisé selon la Charte JO
        lines.append(rf"\pard\sb80\f0\fs22\b Dispositif\~:\b0\par")
        lines.append(rf"\pard\li360\f0\fs22 {rtf_escape(dispositif_normalise)}\par")

        # 6. Exposé sommaire
        lines.append(rf"\pard\sb60\f0\fs20\b Expos\u233? sommaire\~:\b0\par")
        lines.append(rf"\pard\li360\f0\fs20\cf4 {rtf_escape(expose_normalise)}\cf1\par\par")

    lines.append("}")
    return "\n".join(lines)


generate_prejaune_rtf = generer_prejaune_rtf
exporter_prejaune_rtf = generer_prejaune_rtf
