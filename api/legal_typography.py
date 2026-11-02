r"""
api/legal_typography.py — Normalisateur orthotypographique DILA (Journal officiel)
===================================================================================
Implémente de manière 100 % déterministe les règles formelles de :
  1. La « Charte orthotypographique du Journal officiel Lois et décrets » (DILA, janvier 2021, p. 8-10)
  2. Le « Guide de légistique » (Secrétariat général du Gouvernement & Conseil d'État, 2026)

Trois volets principaux :
  - Typographie des articles et des divisions :
      * En début d'alinéa : « Art. 1er. » et « Art. 2. » (avec point final, jamais « 1ier », « 1ère », ni « 2ème »).
      * Pour les articles de lois au long : « Article 1er » et « Article unique » (en toutes lettres).
  - Formulation officielle des subdivisions (interdiction stricte des tirets « Art. 5-III ») :
      * « Article 5-III » ou « Art. 5-III » -> « Le III de l'article 5 »
      * « Article 15-II-6° » -> « Le 6° du II de l'article 15 »
      * « Article 20-I-3°-f » -> « Le f du 3° du I de l'article 20 »
      * « Art. 2 (alinéa 4) » -> « Le quatrième alinéa de l'article 2 » (ordinaux en lettres jusqu'à dix).
  - Micro-typographie et espaces insécables républicaines :
      * Espace insécable (\u00A0 en Unicode/HTML, \~ en RTF) devant « : », « ; », « ! », « ? ».
      * Entre les nombres et les symboles/unités : « 10\u00A0000\u00A0€ », « 15\u00A0% », « 12\u00A0h\u00A030 », « 50\u00A0ans ».
      * Entre l'abréviation et le numéro d'article : « Art.\u00A01er », « art.\u00A02 ».
      * Normalisation des guillemets : «\u00A0...\u00A0» au 1er niveau, "..." au 2e niveau (citations internes).
"""

from __future__ import annotations

import re
from typing import Optional

NBSP = "\u00A0"

_ORDINAUX_ALINEA_LETTRES: dict[int, str] = {
    1: "premier",
    2: "deuxième",
    3: "troisième",
    4: "quatrième",
    5: "cinquième",
    6: "sixième",
    7: "septième",
    8: "huitième",
    9: "neuvième",
    10: "dixième",
}

_LETTRES_VERS_ORDINAL_ALINEA: dict[str, str] = {
    "un": "premier",
    "premier": "premier",
    "1er": "premier",
    "1ier": "premier",
    "1re": "premier",
    "1ère": "premier",
    "1ere": "premier",
    "deux": "deuxième",
    "second": "second",
    "deuxieme": "deuxième",
    "deuxième": "deuxième",
    "2e": "deuxième",
    "2eme": "deuxième",
    "2ème": "deuxième",
    "trois": "troisième",
    "troisieme": "troisième",
    "troisième": "troisième",
    "3e": "troisième",
    "3eme": "troisième",
    "3ème": "troisième",
    "quatre": "quatrième",
    "quatrieme": "quatrième",
    "quatrième": "quatrième",
    "4e": "quatrième",
    "4eme": "quatrième",
    "4ème": "quatrième",
    "cinq": "cinquième",
    "cinquieme": "cinquième",
    "cinquième": "cinquième",
    "5e": "cinquième",
    "5eme": "cinquième",
    "5ème": "cinquième",
    "six": "sixième",
    "sixieme": "sixième",
    "sixième": "sixième",
    "6e": "sixième",
    "6eme": "sixième",
    "6ème": "sixième",
    "sept": "septième",
    "septieme": "septième",
    "septième": "septième",
    "7e": "septième",
    "7eme": "septième",
    "7ème": "septième",
    "huit": "huitième",
    "huitieme": "huitième",
    "huitième": "huitième",
    "8e": "huitième",
    "8eme": "huitième",
    "8ème": "huitième",
    "neuf": "neuvième",
    "neuvieme": "neuvième",
    "neuvième": "neuvième",
    "9e": "neuvième",
    "9eme": "neuvième",
    "9ème": "neuvième",
    "dix": "dixième",
    "dixieme": "dixième",
    "dixième": "dixième",
    "10e": "dixième",
    "10eme": "dixième",
    "10ème": "dixième",
}


def _ordinal_alinea_en_lettres(val: str) -> str:
    """Convertit un numéro ou ordinal d'alinéa en toutes lettres jusqu'à dix."""
    s = val.strip().lower()
    if s.isdigit():
        n = int(s)
        return _ORDINAUX_ALINEA_LETTRES.get(n, f"{n}e")
    if s in _LETTRES_VERS_ORDINAL_ALINEA:
        return _LETTRES_VERS_ORDINAL_ALINEA[s]
    m = re.match(r"^(\d+)(?:i?[eè]me|e|er|ier|[eè]re|re)$", s)
    if m:
        n = int(m.group(1))
        return _ORDINAUX_ALINEA_LETTRES.get(n, f"{n}e")
    return s


def _normaliser_num_article(num_raw: str) -> str:
    """Normalise le numéro d'un article (« 1ier », « 1ère », « premier » -> « 1er », « 2ème » -> « 2 »)."""
    s = re.sub(r"\s+", " ", num_raw.strip())
    low = s.lower()
    if low in ("1", "1er", "1ier", "1re", "1ère", "1ere", "premier", "première", "premiere"):
        return "1er"
    if low == "unique":
        return "unique"
    m_ord = re.match(r"^(\d+)(?:i?[eè]me|e)\b(.*)$", s, flags=re.IGNORECASE)
    if m_ord:
        num = m_ord.group(1)
        reste = m_ord.group(2).strip()
        if num == "1":
            return f"1er {reste}".strip()
        return f"{num} {reste}".strip()
    return s


def _formater_jeton_subdivision(jeton: str) -> str:
    """Formate proprement un échelon de subdivision (ex: '6°', 'II', 'f', 'quatrième alinéa')."""
    j = jeton.strip()
    # Cas alinéa : "alinéa 4" ou "al. 4"
    m_al = re.match(r"^(?:alin[eé]a|al\.?)\s+([0-9a-zA-Zéèê]+)$", j, flags=re.IGNORECASE)
    if m_al:
        ord_lettres = _ordinal_alinea_en_lettres(m_al.group(1))
        return f"{ord_lettres} alinéa"

    # Cas numéro avec degré : "6 °" -> "6°"
    m_deg = re.match(r"^(\d+)\s*°$", j)
    if m_deg:
        return f"{m_deg.group(1)}°"

    # Cas lettre minuscule avec parenthèse fermante éventuelle : "f)" -> "f"
    m_let = re.match(r"^([a-z])\)$", j)
    if m_let:
        return m_let.group(1)

    return j


def _construire_hierarchie_ascendante(
    num_article: str,
    subdivisions: list[str],
    preposition: Optional[str] = None,
) -> str:
    """
    Construit la formulation officielle en hiérarchie ascendante :
      - ['III'] sur art. 5 -> "Le III de l'article 5"
      - ['II', '6°'] sur art. 15 -> "Le 6° du II de l'article 15"
      - ['I', '3°', 'f'] sur art. 20 -> "Le f du 3° du I de l'article 20"
      - ['quatrième alinéa'] sur art. 2 -> "Le quatrième alinéa de l'article 2"
    """
    art_propre = _normaliser_num_article(num_article)
    subs_propres = [_formater_jeton_subdivision(s) for s in subdivisions if s and s.strip()]
    if not subs_propres:
        return f"l'article {art_propre}"

    # Ordre ascendant : de la subdivision la plus fine à la plus large
    ordre_ascendant = list(reversed(subs_propres))
    premier = ordre_ascendant[0]
    parents = ordre_ascendant[1:]

    # Déterminant initial selon la préposition éventuelle qui précède
    prep_norm = (preposition or "").strip()
    prep_lower = prep_norm.lower()
    if prep_lower in ("à l'", "à l’", "a l'", "a l’"):
        amorce = "Au" if prep_norm[0].isupper() else "au"
    elif prep_lower in ("de l'", "de l’"):
        amorce = "Du" if prep_norm[0].isupper() else "du"
    elif prep_lower in ("l'", "l’"):
        amorce = "Le" if prep_norm[0].isupper() else "le"
    else:
        amorce = "Le"

    chaine = f"{amorce} {premier}"
    for p in parents:
        chaine += f" du {p}"

    if art_propre == "unique":
        chaine += " de l'article unique"
    else:
        chaine += f" de l'article {art_propre}"

    return chaine


# Regex pour capturer :
#   1) "Art. 2 (alinéa 4)" ou "Article 5-II (alinéa 3)"
#   2) "Article 5-III", "Art. 15-II-6°", "Article 20-I-3°-f"
_SUBDIVISION_AVEC_ALINEA_PAREN_RE = re.compile(
    r"(?P<prep>(?:[ÀA]|De|de|[àa])\s+l['’]|L['’]|l['’])?"
    r"\b(?:Article|Art\.)\s*"
    r"(?P<art>(?:1er|1ier|1[eè]re|premier|unique|\d+(?:\s*(?:bis|ter|quater|quinquies|sexies|septies|octies|nonies|decies))?))"
    r"(?:[\-–—](?P<subs>(?:[IVXLCDM]+|\d+\s*°|[A-Za-z]|\b(?:alin[eé]a|al\.?)\s+\d+)(?:[\-–—](?:[IVXLCDM]+|\d+\s*°|[A-Za-z]|\b(?:alin[eé]a|al\.?)\s+\d+))*))?"
    r"\s*\(\s*(?:alin[eé]a|al\.?)\s+(?P<alinea>[0-9a-zA-Zéèê]+)\s*\)",
    re.IGNORECASE,
)

_SUBDIVISION_TIRETS_RE = re.compile(
    r"(?P<prep>(?:[ÀA]|De|de|[àa])\s+l['’]|L['’]|l['’])?"
    r"\b(?:Article|Art\.)\s*"
    r"(?P<art>(?:1er|1ier|1[eè]re|premier|unique|\d+(?:\s*(?:bis|ter|quater|quinquies|sexies|septies|octies|nonies|decies))?))"
    r"[\-–—]"
    r"(?P<subs>"
    r"(?:[IVXLCDM]+|\d+\s*°|[A-Za-z]\b|(?:alin[eé]a|al\.?)\s+\d+)"
    r"(?:[\-–—](?:[IVXLCDM]+|\d+\s*°|[A-Za-z]\b|(?:alin[eé]a|al\.?)\s+\d+))*"
    r")",
    re.IGNORECASE,
)


def normaliser_subdivision(texte: str) -> str:
    """
    Remplace automatiquement les graphies abrégées à tirets ou parenthèses par la hiérarchie
    ascendante officielle en toutes lettres (Charte JO & Guide de légistique) :
      - « Article 5-III » ou « Art. 5-III » -> « Le III de l'article 5 »
      - « Article 15-II-6° » -> « Le 6° du II de l'article 15 »
      - « Article 20-I-3°-f » -> « Le f du 3° du I de l'article 20 »
      - « Art. 2 (alinéa 4) » -> « Le quatrième alinéa de l'article 2 »
    """
    if not texte:
        return ""

    def _remplacer_avec_paren(match: re.Match) -> str:
        prep = match.group("prep")
        art = match.group("art")
        subs_str = match.group("subs") or ""
        alinea = match.group("alinea")
        subs = [s for s in re.split(r"[\-–—]", subs_str) if s.strip()] if subs_str else []
        subs.append(f"alinéa {alinea}")
        return _construire_hierarchie_ascendante(art, subs, prep)

    res = _SUBDIVISION_AVEC_ALINEA_PAREN_RE.sub(_remplacer_avec_paren, str(texte))

    def _remplacer_tirets(match: re.Match) -> str:
        prep = match.group("prep")
        art = match.group("art")
        subs_str = match.group("subs")
        subs = [s for s in re.split(r"[\-–—]", subs_str) if s.strip()]
        return _construire_hierarchie_ascendante(art, subs, prep)

    res = _SUBDIVISION_TIRETS_RE.sub(_remplacer_tirets, res)
    return res


def _normaliser_guillemets(texte: str) -> str:
    """
    Normalise les guillemets selon la Charte du Journal officiel :
      - Guillemets français «\u00A0 et \u00A0» (avec espace insécable) au 1er niveau ;
      - Guillemets droits anglais "..." au 2e niveau pour les citations internes.
    """
    if not texte:
        return ""

    s = texte.replace("“", '"').replace("”", '"')

    # Cas 1 : Le texte utilise déjà des guillemets français « ... » (éventuellement imbriqués)
    if "«" in s or "»" in s:
        out: list[str] = []
        depth = 0
        in_inner_straight = False
        i = 0
        n = len(s)
        while i < n:
            ch = s[i]
            if ch == "«":
                depth += 1
                if depth == 1:
                    out.append(f"«{NBSP}")
                else:
                    # 2e niveau (citation interne) -> guillemet droit ouvrant sans espace interne
                    out.append('"')
                # Consommer les espaces immédiatement après le guillemet ouvrant
                i += 1
                while i < n and s[i] in (" ", "\t", NBSP):
                    i += 1
                continue
            if ch == "»":
                # Retirer les espaces immédiatement avant le guillemet fermant
                while out and out[-1] in (" ", "\t", NBSP):
                    out.pop()
                if out and out[-1].endswith((" ", "\t", NBSP)):
                    out[-1] = out[-1].rstrip(f" \t{NBSP}")
                if depth <= 1:
                    out.append(f"{NBSP}»")
                    depth = 0
                else:
                    out.append('"')
                    depth -= 1
                i += 1
                continue
            if ch == '"' and depth >= 1:
                if not in_inner_straight:
                    in_inner_straight = True
                    out.append('"')
                    i += 1
                    while i < n and s[i] in (" ", "\t", NBSP):
                        i += 1
                    continue
                else:
                    while out and out[-1] in (" ", "\t", NBSP):
                        out.pop()
                    if out and out[-1].endswith((" ", "\t", NBSP)):
                        out[-1] = out[-1].rstrip(f" \t{NBSP}")
                    in_inner_straight = False
                    out.append('"')
                    i += 1
                    continue
            out.append(ch)
            i += 1
        return "".join(out)

    # Cas 2 : Le texte ne contient que des guillemets droits "..." -> convertir le 1er niveau en «\u00A0...\u00A0»
    if s.count('"') >= 2 and s.count('"') % 2 == 0:
        out = []
        open_q = False
        i = 0
        n = len(s)
        while i < n:
            ch = s[i]
            if ch == '"':
                if not open_q:
                    open_q = True
                    out.append(f"«{NBSP}")
                    i += 1
                    while i < n and s[i] in (" ", "\t", NBSP):
                        i += 1
                    continue
                else:
                    while out and out[-1] in (" ", "\t", NBSP):
                        out.pop()
                    if out and out[-1].endswith((" ", "\t", NBSP)):
                        out[-1] = out[-1].rstrip(f" \t{NBSP}")
                    open_q = False
                    out.append(f"{NBSP}»")
                    i += 1
                    continue
            out.append(ch)
            i += 1
        return "".join(out)

    return s


def _normaliser_articles_et_ordinaux(texte: str) -> str:
    """
    Applique les règles de la Charte JO (p. 8-10) sur les intitulés d'articles et les ordinaux :
      - Jamais « 1ier », « 1ère », ni « 2ème ».
      - En début d'alinéa : « Art. 1er. » et « Art. 2. » (avec point final).
      - Pour les articles de lois au long : « Article 1er » et « Article unique » (en toutes lettres).
    """
    s = texte

    # 1. Articles de lois au long : « Article 1ier », « Article 1ère », « Article premier », « ARTICLE PREMIER » -> « Article 1er »
    s = re.sub(
        r"\bArticle\s+(?:1ier|1[eè]re|1re|1er|premier|1)\b(?!\d)",
        "Article 1er",
        s,
        flags=re.IGNORECASE,
    )
    # « Article unique » / « Art. unique » -> « Article unique »
    s = re.sub(
        r"\b(?:Article|Art\.)\s+unique\.?",
        "Article unique",
        s,
        flags=re.IGNORECASE,
    )
    # « Article 2ème » -> « Article 2 »
    s = re.sub(
        r"\b(Article|article)\s+(\d+)(?:i?[eè]me|e)\b",
        r"\1 \2",
        s,
    )

    # 2. En début d'alinéa (début de texte, début de ligne, ou juste après «\u00A0) :
    #    « Art. 1er. » et « Art. 2. » avec point final obligatoire.
    def _corriger_art_debut_alinea(match: re.Match) -> str:
        prefix = match.group("prefix")
        num_raw = match.group("num")
        suite = match.group("suite") or ""
        num_norm = _normaliser_num_article(num_raw)
        # Si suivi d'un tiret séparateur (« Art. 1er - Le code... »), conserver l'espace/tiret après le point final
        return f"{prefix}Art.{NBSP}{num_norm}.{suite}"

    s = re.sub(
        r"(?P<prefix>^|\n|«[\s\u00A0]*)"
        r"Art\.\s*(?P<num>1er|1ier|1[eè]re|1re|premier|\d+(?:i?[eè]me|e)?)\s*\.?"
        r"(?P<suite>(?=\s|$|[–—\-]))",
        _corriger_art_debut_alinea,
        s,
        flags=re.IGNORECASE,
    )

    # 3. Dans le reste du texte : « Art. 1ier » -> « Art. 1er », « art. 2ème » -> « art. 2 »
    def _corriger_art_interne(match: re.Match) -> str:
        mot_art = match.group(1)  # "Art." ou "art."
        num_raw = match.group(2)
        dot = match.group(3) or ""
        num_norm = _normaliser_num_article(num_raw)
        return f"{mot_art}{NBSP}{num_norm}{dot}"

    s = re.sub(
        r"\b([Aa]rt\.)[\s\u00A0]*(1er|1ier|1[eè]re|1re|premier|\d+(?:i?[eè]me|e)?)(\.?)",
        _corriger_art_interne,
        s,
    )

    # 4. Correction générale des ordinaux fautifs hors intitulés d'articles :
    #    « 1ier » -> « 1er », « 1ère » -> « 1re », « 2ème » / « 2ième » -> « 2e »
    s = re.sub(r"\b1ier(s?)\b", r"1er\1", s, flags=re.IGNORECASE)
    s = re.sub(r"\b1[eè]re(s?)\b", r"1re\1", s)
    s = re.sub(r"\b(\d+)i?[eè]me(s?)\b", r"\1e\2", s)

    return s


def _inserer_espaces_insecables(texte: str) -> str:
    """
    Insère les espaces insécables républicaines (\u00A0) selon la Charte JO :
      - Devant les ponctuations doubles : « : », « ; », « ! », « ? ».
      - Séparateurs de milliers : « 10 000 » -> « 10\u00A0000 ».
      - Entre les nombres et les symboles/unités : « 10\u00A0000\u00A0€ », « 15\u00A0% », « 12\u00A0h\u00A030 », « 50\u00A0ans ».
      - Entre l'abréviation et le numéro : « Art.\u00A01er », « art.\u00A02 », « n°\u00A012 ».
    """
    s = texte

    # 1. Protéger les schémas d'URL (http://, https://)
    s = s.replace("https://", "__HTTPS_PROTO__").replace("http://", "__HTTP_PROTO__")

    # 2. Séparateurs de milliers (ex: "10 000" -> "10\u00A0000", "1 000 000" -> "1\u00A0000\u00A0000")
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"\b(\d{1,3})[ \t](\d{3})\b", f"\\1{NBSP}\\2", s)

    # 3. Heures : "12 h 30" ou "12h30" -> "12\u00A0h\u00A030", "12 h" -> "12\u00A0h"
    s = re.sub(r"\b(\d{1,2})[ \t\u00A0]*h[ \t\u00A0]*(\d{2})\b", f"\\1{NBSP}h{NBSP}\\2", s)
    s = re.sub(r"\b(\d{1,2})[ \t]+h\b", f"\\1{NBSP}h", s)

    # 4. Nombres suivis de symboles monétaires, pourcentages ou unités courantes :
    #    "10 000 €" -> "10\u00A0000\u00A0€", "15 %" / "15%" -> "15\u00A0%", "50 ans" -> "50\u00A0ans"
    s = re.sub(r"(\d)[ \t\u00A0]*(€|%)", f"\\1{NBSP}\\2", s)
    s = re.sub(
        r"\b(\d+)[ \t]+(ans?|mois|jours?|heures?|minutes?|euros?|millions?|milliards?|km|kg)\b",
        f"\\1{NBSP}\\2",
        s,
    )

    # 5. Abréviations « Art. », « art. », « n° », « N° » suivies d'un numéro
    s = re.sub(r"\b([Aa]rt\.)[ \t]+(\d|1er)", f"\\1{NBSP}\\2", s)
    s = re.sub(r"([nN]°)[ \t]*(\d)", f"\\1{NBSP}\\2", s)

    # 6. Signes de ponctuation doubles : « : », « ; », « ! », « ? »
    s = re.sub(r"[ \t\u00A0]*([:;!?])", f"{NBSP}\\1", s)
    # Éviter de doubler l'espace insécable si le début de chaîne commençait par une ponctuation
    s = re.sub(rf"^{NBSP}([:;!?])", r"\1", s)

    # Restaurer les URLs éventuelles
    s = s.replace("__HTTPS_PROTO__", "https://").replace("__HTTP_PROTO__", "http://")
    return s


def normaliser_typographie_jo(texte: str) -> str:
    """
    Normalise intégralement un texte législatif selon la Charte orthotypographique
    du Journal officiel (DILA, janvier 2021) :
      1. Conversion des subdivisions à tirets ou parenthèses en hiérarchie ascendante.
      2. Typographie des articles (« Art.\u00A01er. », « Art.\u00A02. », « Article 1er », « Article unique »)
         et correction des ordinaux (« 1ier » -> « 1er », « 1ère » -> « 1re », « 2ème » -> « 2e »).
      3. Normalisation des guillemets (1er niveau «\u00A0...\u00A0», 2e niveau "...").
      4. Insertion systématique des espaces insécables (\u00A0) devant `:`, `;`, `!`, `?`,
         entre nombres et unités (`€`, `%`, `h`, `ans`) et après `Art.` / `art.`.
    """
    if not texte:
        return ""

    s = str(texte)
    s = normaliser_subdivision(s)
    s = _normaliser_articles_et_ordinaux(s)
    s = _normaliser_guillemets(s)
    s = _inserer_espaces_insecables(s)
    return s


def convertir_espaces_insecables_rtf(texte: str) -> str:
    """Remplace les espaces insécables Unicode (\u00A0) par le code RTF officiel `\\~`."""
    if not texte:
        return ""
    return texte.replace(NBSP, r"\~")


try:
    from api.legal_chapeau_parser import (
        MOTIF_NON_NORMATIF_DEFAUT,
        auditer_portee_normative,
        detecter_dispositions_non_normatives,
        detecter_non_normatif,
    )
except ModuleNotFoundError:
    from legal_chapeau_parser import (  # type: ignore
        MOTIF_NON_NORMATIF_DEFAUT,
        auditer_portee_normative,
        detecter_dispositions_non_normatives,
        detecter_non_normatif,
    )

__all__ = [
    "NBSP",
    "normaliser_subdivision",
    "normaliser_typographie_jo",
    "convertir_espaces_insecables_rtf",
    "detecter_dispositions_non_normatives",
    "auditer_portee_normative",
    "detecter_non_normatif",
    "MOTIF_NON_NORMATIF_DEFAUT",
]

