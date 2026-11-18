"""
api/legal_chapeau_parser.py — Analyseur légistique AN/Sénat, Dérouleur de séance & Auditeur Article 40
======================================================================================================
Implémente de manière 100 % déterministe les règles officielles de légistique formelle et de
procédure parlementaire française issues :
  1. Du « Guide pour la rédaction des amendements » de l'Assemblée nationale (Octobre 2021)
  2. Du guide « La rédaction des amendements, sous-amendements et motions de procédure » du Sénat (Septembre 2025)

Trois briques fondamentales :
  - Chantier 1 : Extraction syntaxique du « chapeau » (7 verbes cardinaux, ciblage anatomique,
                 pastillage en marge, règle ordinale des phrases Sénat p. 26, occurrences multiples).
  - Chantier 2 : Calculateur mathématique d'ordre d'appel au « Dérouleur de séance »
                 (`calculer_priorite_derouleur`).
  - Chantier 3 : Auditeur constitutionnel de recevabilité financière au titre de l'Article 40
                 de la Constitution (pertes de recettes, charges publiques, 4 gages sacramentels
                 et clause impérative sur les crédits d'impôt Sénat p. 65).
"""

from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from enum import Enum
from typing import Any, Optional, Union


# ──────────────────────────────────────────────────────────────────────────
# 1. Énumérations et constantes légistiques (AN p. 10-13, Sénat p. 32-34)
# ──────────────────────────────────────────────────────────────────────────

class VerbeAction(str, Enum):
    """Les 7 verbes cardinaux d'action du chapeau d'amendement (avec distinction REMPLACER / SUBSTITUER)."""
    SUPPRIMER = "SUPPRIMER"
    REDIGER_AINSI = "REDIGER_AINSI"
    REMPLACER = "REMPLACER"
    SUBSTITUER = "SUBSTITUER"
    INSERER = "INSERER"
    AJOUTER = "AJOUTER"
    COMPLETER = "COMPLETER"
    RETABLIR = "RETABLIR"


class CibleType(str, Enum):
    """Éléments anatomiques amendables (AN p. 5-8, Sénat p. 25-27)."""
    ARTICLE = "ARTICLE"
    DIVISION = "DIVISION"
    INTITULE = "INTITULE"
    ALINEA = "ALINEA"
    PHRASE = "PHRASE"
    TABLEAU = "TABLEAU"
    ANNEXE = "ANNEXE"
    MOTS = "MOTS"


_NOMBRES_LETTRES: dict[str, int] = {
    "un": 1,
    "une": 1,
    "premier": 1,
    "premiere": 1,
    "première": 1,
    "deux": 2,
    "second": 2,
    "seconde": 2,
    "deuxieme": 2,
    "deuxième": 2,
    "trois": 3,
    "troisieme": 3,
    "troisième": 3,
    "quatre": 4,
    "quatrieme": 4,
    "quatrième": 4,
    "cinq": 5,
    "cinquieme": 5,
    "cinquième": 5,
    "six": 6,
    "sixieme": 6,
    "sixième": 6,
    "sept": 7,
    "septieme": 7,
    "septième": 7,
    "huit": 8,
    "huitieme": 8,
    "huitième": 8,
    "neuf": 9,
    "neuvieme": 9,
    "neuvième": 9,
    "dix": 10,
    "dixieme": 10,
    "dixième": 10,
}

_ORDINAUX_PHRASE_RANG: dict[str, int] = {
    "premiere": 1,
    "première": 1,
    "1re": 1,
    "1ere": 1,
    "1ère": 1,
    "seconde": 2,
    "deuxieme": 2,
    "deuxième": 2,
    "2e": 2,
    "2eme": 2,
    "2ème": 2,
    "troisieme": 3,
    "troisième": 3,
    "3e": 3,
    "3eme": 3,
    "3ème": 3,
    "quatrieme": 4,
    "quatrième": 4,
    "4e": 4,
    "cinquieme": 5,
    "cinquième": 5,
    "5e": 5,
    "sixieme": 6,
    "sixième": 6,
    "6e": 6,
    "septieme": 7,
    "septième": 7,
    "7e": 7,
    "avant-derniere": 8,
    "avant-dernière": 8,
    "avant derniere": 8,
    "avant dernière": 8,
    "derniere": 9,
    "dernière": 9,
}

_RANG_VERS_ORDINAL_FEMININ: dict[int, str] = {
    1: "première",
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

_RANG_VERS_ORDINAL_MASCULIN: dict[int, str] = {
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


# ──────────────────────────────────────────────────────────────────────────
# Utilitaires de nettoyage et normalisation
# ──────────────────────────────────────────────────────────────────────────

def _strip_html(raw: Any) -> str:
    """Nettoie les balises HTML et décode les entités en préservant les sauts de ligne structurels."""
    if not raw:
        return ""
    s = html.unescape(str(raw))
    s = re.sub(r"<(?:br|/p|/div)[^>]*>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = s.replace("\xa0", " ").replace("&#160;", " ").replace("&nbsp;", " ")
    s = s.replace("&#x2011;", "-").replace("\u2011", "-")
    s = s.replace("&laquo;", "«").replace("&raquo;", "»")
    s = s.replace("&rsquo;", "’").replace("&lsquo;", "‘")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


def _deaccent(text: str) -> str:
    """Retire les accents d'une chaîne tout en conservant la casse ou en normalisant."""
    return unicodedata.normalize("NFKD", text or "").encode("ASCII", "ignore").decode("utf-8")


def _fingerprint_text(text: str) -> str:
    """Empreinte canonique d'un dispositif pour le regroupement des amendements identiques au dérouleur."""
    clean = _strip_html(text)
    norm = _deaccent(clean).lower()
    norm = re.sub(r"[^\w\s]", " ", norm)
    norm = re.sub(r"\s+", " ", norm).strip()
    if not norm:
        return ""
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


# ──────────────────────────────────────────────────────────────────────────
# Règle ordinale du Sénat (Sénat p. 26)
# ──────────────────────────────────────────────────────────────────────────

def qualifier_ordinal_senat(rang: int, nb_composants: int, feminin: bool = True) -> str:
    """
    Retourne la dénomination ordinale officielle selon la règle stricte du Sénat (p. 26) :
      - 2 composants : le 2e est obligatoirement « seconde » (F) / « second » (M).
      - >= 3 composants : le 2e est « deuxième », le dernier est « dernière » / « dernier ».
      - 4 composants : le 3e est « troisième » (jamais « avant-dernière »).
      - >= 5 composants : l'élément (N - 1) est « avant-dernière » / « avant-dernier ».
    """
    if nb_composants < 1 or rang < 1 or rang > nb_composants:
        raise ValueError(f"Rang ({rang}) ou nombre de composants ({nb_composants}) invalide.")

    if nb_composants == 1:
        return "unique"

    if rang == 1:
        return "première" if feminin else "premier"

    if nb_composants == 2:
        # Règle Sénat p. 26 : « Pour désigner le deuxième alinéa/phrase, qui est aussi le dernier, on parle du second / de la seconde »
        return "seconde" if feminin else "second"

    # nb_composants >= 3
    if rang == nb_composants:
        return "dernière" if feminin else "dernier"

    if rang == nb_composants - 1 and nb_composants >= 5:
        return "avant-dernière" if feminin else "avant-dernier"

    table = _RANG_VERS_ORDINAL_FEMININ if feminin else _RANG_VERS_ORDINAL_MASCULIN
    return table.get(rang, f"{rang}e")


def valider_ordinal_phrase(terme_ordinal: str, nb_composants: Optional[int] = None) -> dict[str, Any]:
    """
    Valide et normalise un ordinal de phrase selon la règle du Sénat (p. 26) :
      - « seconde » uniquement si l'élément n'a que 2 composants ;
      - « deuxième », « troisième » si >= 3 composants ;
      - « avant-dernière » uniquement recevable si l'élément comporte au moins 5 composants.

    Returns:
        dict avec :
          - `terme_initial` (str)
          - `rang_numerique` (int)
          - `ordinal_normalise` (str)
          - `recevable` (bool)
          - `motif` (str | None)
    """
    raw = (terme_ordinal or "").strip().lower()
    raw_norm = re.sub(r"\s+", " ", raw).replace("–", "-")
    rang = _ORDINAUX_PHRASE_RANG.get(raw_norm) or _ORDINAUX_PHRASE_RANG.get(_deaccent(raw_norm), 0)

    # Normalisation de l'orthographe française de base
    if "avant" in raw_norm and "dernier" in _deaccent(raw_norm):
        terme_propre = "avant-dernière"
        rang = 8
    elif "dernier" in _deaccent(raw_norm):
        terme_propre = "dernière"
        rang = 9
    elif "second" in _deaccent(raw_norm):
        terme_propre = "seconde"
        rang = 2
    elif "deuxi" in _deaccent(raw_norm) or raw_norm in ("2e", "2eme", "2ème"):
        terme_propre = "deuxième"
        rang = 2
    elif "troisi" in _deaccent(raw_norm) or raw_norm in ("3e", "3eme", "3ème"):
        terme_propre = "troisième"
        rang = 3
    elif "premi" in _deaccent(raw_norm) or raw_norm in ("1re", "1ere", "1ère"):
        terme_propre = "première"
        rang = 1
    else:
        terme_propre = _RANG_VERS_ORDINAL_FEMININ.get(rang, raw_norm)

    if nb_composants is None:
        return {
            "terme_initial": terme_ordinal,
            "rang_numerique": rang,
            "ordinal_normalise": terme_propre,
            "recevable": True,
            "motif": None,
        }

    # Vérification stricte avec nb_composants connu (Sénat p. 26)
    if terme_propre == "seconde":
        if nb_composants == 2:
            return {
                "terme_initial": terme_ordinal,
                "rang_numerique": 2,
                "ordinal_normalise": "seconde",
                "recevable": True,
                "motif": None,
            }
        attendu = qualifier_ordinal_senat(2, nb_composants, feminin=True)
        return {
            "terme_initial": terme_ordinal,
            "rang_numerique": 2,
            "ordinal_normalise": attendu,
            "recevable": False,
            "motif": (
                f"Irrecevabilité légistique (Sénat p. 26) : « seconde » ne s'emploie que lorsque "
                f"l'élément comporte exactement 2 composants (ici {nb_composants}). Utiliser « {attendu} »."
            ),
        }

    if terme_propre == "deuxième":
        if nb_composants == 2:
            return {
                "terme_initial": terme_ordinal,
                "rang_numerique": 2,
                "ordinal_normalise": "seconde",
                "recevable": False,
                "motif": (
                    "Irrecevabilité légistique (Sénat p. 26) : lorsque l'élément ne comporte que "
                    "2 composants, la 2e phrase (qui est aussi la dernière) doit être désignée "
                    "comme « seconde » et non « deuxième »."
                ),
            }
        return {
            "terme_initial": terme_ordinal,
            "rang_numerique": 2,
            "ordinal_normalise": "deuxième",
            "recevable": nb_composants >= 3,
            "motif": None if nb_composants >= 3 else "Nombre de composants insuffisant.",
        }

    if terme_propre == "avant-dernière":
        rang_reel = max(1, nb_composants - 1)
        if nb_composants < 5:
            attendu = qualifier_ordinal_senat(rang_reel, nb_composants, feminin=True)
            return {
                "terme_initial": terme_ordinal,
                "rang_numerique": rang_reel,
                "ordinal_normalise": attendu,
                "recevable": False,
                "motif": (
                    f"Irrecevabilité légistique (Sénat p. 26) : la dénomination « avant-dernière » "
                    f"n'est recevable que lorsque l'on dénombre au minimum 5 composants "
                    f"(ici {nb_composants}). Utiliser « {attendu} »."
                ),
            }
        return {
            "terme_initial": terme_ordinal,
            "rang_numerique": rang_reel,
            "ordinal_normalise": "avant-dernière",
            "recevable": True,
            "motif": None,
        }

    if terme_propre == "dernière":
        rang_reel = nb_composants
        if nb_composants == 2:
            return {
                "terme_initial": terme_ordinal,
                "rang_numerique": 2,
                "ordinal_normalise": "seconde",
                "recevable": False,
                "motif": (
                    "Irrecevabilité légistique (Sénat p. 26) : pour 2 composants, "
                    "utiliser « seconde » et non « dernière »."
                ),
            }
        return {
            "terme_initial": terme_ordinal,
            "rang_numerique": rang_reel,
            "ordinal_normalise": "dernière",
            "recevable": nb_composants >= 3,
            "motif": None,
        }

    if terme_propre == "troisième":
        if nb_composants == 3:
            return {
                "terme_initial": terme_ordinal,
                "rang_numerique": 3,
                "ordinal_normalise": "dernière",
                "recevable": False,
                "motif": (
                    "Irrecevabilité légistique (Sénat p. 26) : dans un élément à 3 composants, "
                    "le 3e composant doit être désigné comme « dernière » et non « troisième »."
                ),
            }
        return {
            "terme_initial": terme_ordinal,
            "rang_numerique": 3,
            "ordinal_normalise": "troisième",
            "recevable": nb_composants >= 4,
            "motif": None if nb_composants >= 4 else "Nombre de composants insuffisant pour « troisième ».",
        }

    attendu = qualifier_ordinal_senat(min(rang, nb_composants), nb_composants, feminin=True)
    return {
        "terme_initial": terme_ordinal,
        "rang_numerique": rang,
        "ordinal_normalise": attendu,
        "recevable": (terme_propre == attendu),
        "motif": None if (terme_propre == attendu) else f"Attendu « {attendu} » pour {nb_composants} composants.",
    }


# ──────────────────────────────────────────────────────────────────────────
# CHANTIER 1 : Extraction syntaxique du chapeau
# ──────────────────────────────────────────────────────────────────────────

class ChapeauAnalysis(dict):
    """
    Dictionnaire enrichi permettant à la fois l'accès par clé (`res["verbe"]`)
    et l'accès par attribut (`res.verbe`, `res.verbe_action`, `res.cible_type`, etc.).
    """
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(f"'ChapeauAnalysis' object has no attribute '{name}'") from exc

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


_COUPURE_CORPS_REDIGE_RE = re.compile(
    r"("
    r"ainsi\s+r[eé]dig[eé][es]*|"
    r"dans\s+la\s+r[eé]daction\s+suivante|"
    r"(?:article|alin[eé]as?|phrases?|paragraphes?|division|intitul[eé]|tableau|annexe|lignes?)\s+suivant[es]*|"
    r"r[eé]diger\s+ainsi\s+(?:cet\s+article|l['’\s]*article[^:]*|cet\s+alin[eé]a|ces\s+alin[eé]as|l['’\s]*alin[eé]a[^:]*|les\s+alin[eé]as[^:]*|cette\s+phrase|ces\s+phrases|la\s+[^:]*phrase[^:]*|ce\s+paragraphe|ce\s+tableau|cette\s+annexe|cet\s+intitul[eé]|l['’\s]*intitul[eé][^:]*|le\s+d[eé]but\s+de[^:]*|la\s+fin\s+de[^:]*)"
    r")\s*:",
    re.IGNORECASE,
)

_COUPURE_GAGE_II_RE = re.compile(
    r"\b(?:II|III|IV)\s*[.\-–—]+\s*(?:Pour\s+compenser\s+la\s+perte\s+de\s+recettes|La\s+perte\s+de\s+recettes|Compl[eé]ter\s+cet\s+article\s+par[^\n]*perte\s+de\s+recettes)",
    re.IGNORECASE,
)


def extraire_chapeau_brut(dispositif: str) -> str:
    """
    Isole l'instruction légistique (« chapeau ») du corps rédigé et des paragraphes de gage.
    Préserve intégralement les chapeaux de substitution ou suppression de mots qui
    contiennent des deux-points avant le verbe (ex: « Après le mot : « X », supprimer la fin de l'alinéa Y »).
    """
    clean = _strip_html(dispositif)
    if not clean:
        return ""

    # 1. Retirer l'éventuel paragraphe II/III de gage financier
    m_gage = _COUPURE_GAGE_II_RE.search(clean)
    if m_gage:
        clean = clean[:m_gage.start()].strip()

    # 2. Couper après les formules introduisant un bloc rédigé (« ainsi rédigé : », « Rédiger ainsi cet article : », etc.)
    m_corps = _COUPURE_CORPS_REDIGE_RE.search(clean)
    if m_corps:
        return clean[:m_corps.end()].strip()

    return clean


def _masquer_citations(chapeau: str) -> str:
    """
    Remplace le contenu entre guillemets français (« ... ») ou droits ("...") par un jeton neutre
    afin que les mots cités ne soient jamais confondus avec les verbes ou cibles du chapeau.
    """
    s = re.sub(r"«[^»]*»", " « __CIT__ » ", chapeau)
    s = re.sub(r'"[^"]*"', ' " __CIT__ " ', s)
    return s


def _extraire_verbe_cardinal(chapeau_masque: str, chapeau_original: str) -> tuple[str, str]:
    """
    Extrait le verbe cardinal parmi les 7 catégories officielles :
      - SUPPRIMER
      - REDIGER_AINSI
      - REMPLACER / SUBSTITUER
      - INSERER
      - AJOUTER
      - COMPLETER
      - RETABLIR

    Retourne (verbe_specifique, verbe_cardinal).
    """
    s = _deaccent(chapeau_masque).lower()

    # Retirer les formules passives finales d'introduction (« ainsi redige(s) ») pour ne pas gêner
    s_sans_ainsi_redige = re.sub(r"\bainsi\s+redig[eé][es]*\b", "", s)

    # 1. RETABLIR (« Rétablir cet article... », « À l'alinéa 6, rétablir le IV... »)
    if re.search(r"\bretablir\b", s_sans_ainsi_redige):
        return (VerbeAction.RETABLIR.value, VerbeAction.RETABLIR.value)

    # 2. REDIGER_AINSI (« Rédiger ainsi cet article : », « À l'alinéa 5, rédiger ainsi la première phrase : »)
    if re.search(r"\brediger\s+ainsi\b", s_sans_ainsi_redige) or re.search(r"\best\s+ainsi\s+redige[es]*\b", s):
        return (VerbeAction.REDIGER_AINSI.value, VerbeAction.REDIGER_AINSI.value)

    # 3. REMPLACER / SUBSTITUER
    if re.search(r"\bsubstituer\b", s_sans_ainsi_redige):
        return (VerbeAction.SUBSTITUER.value, VerbeAction.SUBSTITUER.value)
    if re.search(r"\b(?:remplacer|est\s+remplace[es]*|sont\s+remplace[es]*)\b", s_sans_ainsi_redige):
        return (VerbeAction.REMPLACER.value, VerbeAction.REMPLACER.value)

    # 4. AJOUTER (« Au début, ajouter les deux alinéas suivants : », « Au début de l'alinéa 1, ajouter... »)
    if re.search(r"\b(?:ajouter|sont\s+ajoute[es]*|il\s+est\s+ajoute)\b", s_sans_ainsi_redige):
        return (VerbeAction.AJOUTER.value, VerbeAction.AJOUTER.value)

    # 5. COMPLETER (« Compléter cet article par... », « Compléter l'alinéa 4 par... »)
    if re.search(r"\b(?:completer|est\s+complete[es]*)\b", s_sans_ainsi_redige):
        return (VerbeAction.COMPLETER.value, VerbeAction.COMPLETER.value)

    # 6. INSERER (« Après l'alinéa 4, insérer... », « Après le mot X, insérer... »)
    if re.search(r"\b(?:inserer|est\s+insere[es]*|sont\s+insere[es]*)\b", s_sans_ainsi_redige):
        return (VerbeAction.INSERER.value, VerbeAction.INSERER.value)

    # 7. SUPPRIMER (« Supprimer cet article. », « Supprimer les alinéas 3 à 5. », « supprimer la fin de... »)
    if re.search(r"\b(?:supprimer|est\s+supprime[es]*|sont\s+supprime[es]*|est\s+abroge[es]*|supprime[es]*)\b", s_sans_ainsi_redige):
        return (VerbeAction.SUPPRIMER.value, VerbeAction.SUPPRIMER.value)

    # Fallback si citation masquée contenait le verbe par erreur de guillemets mal fermés
    s_orig = _deaccent(chapeau_original).lower()
    if re.search(r"\bretablir\b", s_orig):
        return (VerbeAction.RETABLIR.value, VerbeAction.RETABLIR.value)
    if re.search(r"\brediger\s+ainsi\b", s_orig):
        return (VerbeAction.REDIGER_AINSI.value, VerbeAction.REDIGER_AINSI.value)
    if re.search(r"\bsubstituer\b", s_orig):
        return (VerbeAction.SUBSTITUER.value, VerbeAction.SUBSTITUER.value)
    if re.search(r"\bremplacer\b", s_orig):
        return (VerbeAction.REMPLACER.value, VerbeAction.REMPLACER.value)
    if re.search(r"\bajouter\b", s_orig):
        return (VerbeAction.AJOUTER.value, VerbeAction.AJOUTER.value)
    if re.search(r"\bcompleter\b", s_orig):
        return (VerbeAction.COMPLETER.value, VerbeAction.COMPLETER.value)
    if re.search(r"\binserer\b", s_orig):
        return (VerbeAction.INSERER.value, VerbeAction.INSERER.value)
    if re.search(r"\bsupprimer\b", s_orig):
        return (VerbeAction.SUPPRIMER.value, VerbeAction.SUPPRIMER.value)

    return ("", "")


def _extraire_alinea_num(chapeau_masque: str) -> tuple[Optional[int], Optional[int], list[int]]:
    """
    Extrait le numéro de pastille d'alinéa en marge (chiffre arabe prioritaire) ainsi que
    les plages éventuelles (« alinéas 3 à 5 », « alinéas 2, 4 et 7 »).
    """
    s = _deaccent(chapeau_masque).lower()

    # 1. Plage d'alinéas : « alinéas 3 à 5 » ou « alinéas 3 et 4 »
    m_plage = re.search(r"\balineas?\s+(\d+)\s+a\s+(\d+)\b", s)
    if m_plage:
        debut, fin = int(m_plage.group(1)), int(m_plage.group(2))
        if debut <= fin and (fin - debut) <= 500:
            return (debut, fin, list(range(debut, fin + 1)))
        return (debut, fin, [debut, fin])

    # 2. Énumération d'alinéas : « alinéas 2, 4 et 7 »
    m_enum = re.search(r"\balineas\s+(\d+(?:\s*,\s*\d+)*(?:\s+et\s+\d+)?)\b", s)
    if m_enum:
        nums = [int(x) for x in re.findall(r"\d+", m_enum.group(1))]
        if nums:
            return (nums[0], nums[-1], nums)

    # 3. Pastillage en marge officiel (chiffre arabe) : « alinéa 5 », « de l'alinéa 6 »
    # Note AN p. 8 : « Au troisième alinéa du II de l'alinéa 6 » -> le dernier « alinéa <chiffre> »
    # ou le numéro arabe est la pastille en marge.
    arabes = [int(x) for x in re.findall(r"\balineas?\s+(\d+)\b", s)]
    if arabes:
        return (arabes[-1], arabes[-1], [arabes[-1]])

    # 4. Cas où un identifiant symbolique est utilisé dans un test générique (« l'alinéa Y »)
    # ou un ordinal en toutes lettres (« Au premier alinéa », « Au second alinéa »)
    m_ord = re.search(
        r"\b(?:au|du|le|l)\s+(premier|second|deuxieme|troisieme|quatrieme|cinquieme|sixieme|septieme|huitieme|neuvieme|dixieme)\s+alinea\b",
        s,
    )
    if m_ord:
        val = _NOMBRES_LETTRES.get(m_ord.group(1))
        if val:
            return (val, val, [val])

    return (None, None, [])


def _extraire_rang_phrase(
    chapeau_masque: str,
    nb_composants: Optional[int] = None,
) -> tuple[Optional[int], Optional[str], bool, Optional[str]]:
    """
    Extrait le rang de la phrase visée et applique la normalisation ordinale Sénat (p. 26).
    Retourne (rang_phrase_int, ordinal_normalise, ordinal_recevable, motif_ordinal).
    """
    s = chapeau_masque.lower()
    s_deacc = _deaccent(s)

    # Cas 1 : « avant-dernière phrase » / « avant-dernière et dernière phrases »
    if re.search(r"\bavant[\s\-]+derniere\s+(?:et\s+derniere\s+)?phrases?\b", s_deacc):
        v = valider_ordinal_phrase("avant-dernière", nb_composants)
        return (v["rang_numerique"], v["ordinal_normalise"], v["recevable"], v["motif"])

    # Cas 2 : « première et deuxième phrases » / « deux premières phrases » / « quatre premières phrases »
    if re.search(r"\b(?:premiere\s+et\s+(?:deuxieme|seconde)|(?:\w+\s+)?premieres)\s+phrases\b", s_deacc):
        v = valider_ordinal_phrase("première", nb_composants)
        return (v["rang_numerique"], v["ordinal_normalise"], v["recevable"], v["motif"])

    # Cas 3 : Ordinal standard devant « phrase(s) »
    m = re.search(
        r"\b(premi[eè]re|1re|1[eè]re|seconde|deuxi[eè]me|2e|2[eè]me|troisi[eè]me|3e|3[eè]me|"
        r"quatri[eè]me|4e|cinqui[eè]me|5e|sixi[eè]me|6e|septi[eè]me|7e|"
        r"avant[\s\-]+derni[eè]re|derni[eè]re)\s+phrases?\b",
        s,
    )
    if m:
        terme_brut = m.group(1)
        v = valider_ordinal_phrase(terme_brut, nb_composants)
        return (v["rang_numerique"], v["ordinal_normalise"], v["recevable"], v["motif"])

    return (None, None, True, None)


def _extraire_occurrence_mots(chapeau: str) -> tuple[Optional[int], Optional[str]]:
    """
    Détecte les occurrences multiples ou ciblées de mots (AN p. 10, Sénat p. 18, 44, 46) :
      - « supprimer (trois fois) le mot X » -> (3, "trois fois")
      - « remplacer deux fois le montant » -> (2, "deux fois")
      - « supprimer les trois occurrences du mot X » -> (3, "trois occurrences")
      - « remplacer les deux premières occurrences des mots » -> (2, "deux premières occurrences")
      - « supprimer la seconde occurrence du mot Y » -> (2, "seconde occurrence")
    """
    s = _deaccent(chapeau).lower()

    # 1. « (trois fois) » ou « quatre fois »
    m_fois = re.search(r"\(?\b(un|une|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|\d+)\s+fois\b\)?", s)
    if m_fois:
        tok = m_fois.group(1)
        nb = int(tok) if tok.isdigit() else _NOMBRES_LETTRES.get(tok, 1)
        return (nb, f"{tok} fois")

    # 2. « les trois occurrences » / « les deux premières occurrences »
    m_plur = re.search(
        r"\bles\s+(deux|trois|quatre|cinq|six|sept|huit|neuf|dix|\d+)\s+(?:(?:premieres?|dernieres?)\s+)?occurrences?\b",
        s,
    )
    if m_plur:
        tok = m_plur.group(1)
        nb = int(tok) if tok.isdigit() else _NOMBRES_LETTRES.get(tok, 1)
        return (nb, m_plur.group(0).replace("les ", "").strip())

    # 3. « la seconde occurrence » / « la première occurrence » / « la troisième occurrence »
    m_sing = re.search(
        r"\bla\s+(premiere|seconde|deuxieme|troisieme|quatrieme|cinquieme|avant-derniere|derniere)\s+occurrence\b",
        s,
    )
    if m_sing:
        tok = m_sing.group(1)
        rang = _ORDINAUX_PHRASE_RANG.get(tok, 1)
        # Restituer l'accent sur seconde / première / deuxième si présent
        label_ord = "seconde" if tok == "seconde" else _RANG_VERS_ORDINAL_FEMININ.get(rang, tok)
        return (rang, f"{label_ord} occurrence")

    return (None, None)


def _determiner_cible_type(
    chapeau_masque: str,
    verbe: str,
    alinea_num: Optional[int],
    rang_phrase: Optional[int],
) -> str:
    """
    Détermine la cible anatomique principale (`cible_type`) parmi :
      `ARTICLE`, `DIVISION`, `INTITULE`, `ALINEA`, `PHRASE`, `TABLEAU`, `ANNEXE`, `MOTS`.
    """
    s = _deaccent(chapeau_masque).lower()

    # 1. ANNEXE (AN 1.7, Sénat V.B)
    if re.search(r"\b(?:annexes?|rapport\s+annexe|etats?\s+annexes?)\b", s):
        return CibleType.ANNEXE.value

    # 2. TABLEAU (AN 1.8, Sénat V.A)
    if re.search(r"\b(?:tableaux?|colonnes?\s+du\s+tableau|lignes?\s+du\s+tableau)\b", s):
        return CibleType.TABLEAU.value

    # 3. INTITULE (AN 1.1 & 1.2, Sénat II.A & II.B)
    if re.search(r"\b(?:intitules?|au\s+titre\s+du\s+projet|au\s+titre\s+de\s+la\s+proposition|titre\s+du\s+projet)\b", s):
        return CibleType.INTITULE.value

    # 4. DIVISION (AN 1.2 & 3.2.2, Sénat II.B & II.I)
    if re.search(r"\b(?:cette\s+division|la\s+division|une\s+division)\b", s):
        return CibleType.DIVISION.value
    if re.search(r"\bretablir\s+le\s+[ivxlcdm]+\b", s):
        return CibleType.DIVISION.value if alinea_num is None else CibleType.ALINEA.value

    # 5. Action directe au niveau de l'ARTICLE entier
    #    Ex: « Supprimer cet article. », « Rédiger ainsi cet article : »,
    #        « Rétablir cet article... », « Compléter cet article par... »,
    #        « Après l'article 15, insérer l'article suivant : »
    if alinea_num is None and rang_phrase is None:
        if re.search(
            r"\b(?:cet\s+article|l['’\s]*article\s+(?:premier|1er|unique|suivant|\d+)|article\s+additionnel)\b",
            s,
        ):
            # Si on complète cet article (même par des mots) ou supprime/rédige/rétablit/insère cet article
            if verbe in (
                VerbeAction.SUPPRIMER.value,
                VerbeAction.REDIGER_AINSI.value,
                VerbeAction.RETABLIR.value,
                VerbeAction.COMPLETER.value,
                VerbeAction.INSERER.value,
            ):
                # Exception : « À l'article X, supprimer le mot Y » (sans « cet article » comme objet direct)
                if verbe == VerbeAction.SUPPRIMER.value and re.search(r"\bsupprimer\s+(?:le\s+mot|les\s+mots)\b", s):
                    return CibleType.MOTS.value
                return CibleType.ARTICLE.value

    # 6. MOTS (En deçà de la phrase : AN 1.6, Sénat p. 27)
    #    Lorsque le verbe porte directement sur des mots, montants, nombres, dates, années, références, taux
    if re.search(
        r"\b(?:substituer|remplacer|supprimer|inserer|ajouter|completer)\b[^:]*?"
        r"\b(?:le\s+mot|les\s+mots|au\s+mot|aux\s+mots|du\s+mot|des\s+mots|"
        r"occurrence\s+du\s+mot|occurrences?\s+d(?:u|es)\s+mots?|"
        r"le\s+montant|les\s+montants|au\s+montant|"
        r"le\s+nombre|les\s+nombres|au\s+nombre|"
        r"le\s+chiffre|les\s+chiffres|au\s+chiffre|"
        r"l['’\s]*annee|la\s+date|la\s+reference|les\s+references|"
        r"le\s+taux|au\s+taux|le\s+pourcentage)\b",
        s,
    ):
        # Si c'est « Compléter l'alinéa 4 par la phrase suivante », « phrase » est l'objet et non « mot »
        if not re.search(r"\b(?:completer|ajouter|inserer)\b[^:]*\b(?:phrase|alinea)s?\s+suivant", s):
            return CibleType.MOTS.value

    # 7. PHRASE (AN 1.5, Sénat p. 26)
    if rang_phrase is not None or re.search(r"\b(?:cette\s+phrase|ces\s+phrases|la\s+phrase\s+suivante|les\s+\w+\s+phrases\s+suivantes|une\s+phrase\s+ainsi\s+redigee)\b", s):
        return CibleType.PHRASE.value

    # 8. ALINEA (AN 1.4, Sénat p. 25)
    if alinea_num is not None or re.search(r"\b(?:cet\s+alinea|ces\s+alineas|alineas?\s+suivants?|alineas?\s+ainsi\s+rediges?|fin\s+de\s+l['’\s]*alinea)\b", s):
        return CibleType.ALINEA.value

    # Repli par défaut
    if "article" in s:
        return CibleType.ARTICLE.value
    return CibleType.ALINEA.value


def parse_chapeau(
    texte: str,
    nb_composants: Optional[int] = None,
) -> ChapeauAnalysis:
    """
    Analyse syntaxiquement le chapeau d'un amendement (AN / Sénat) et extrait :
      - `verbe` / `verbe_action` : parmi les 7 verbes cardinaux (`SUPPRIMER`, `REDIGER_AINSI`,
        `REMPLACER` / `SUBSTITUER`, `INSERER`, `AJOUTER`, `COMPLETER`, `RETABLIR`)
      - `cible_type` : `ARTICLE`, `DIVISION`, `INTITULE`, `ALINEA`, `PHRASE`, `TABLEAU`, `ANNEXE`, `MOTS`
      - `alinea_num` : numéro de pastille en marge (int | None)
      - `rang_phrase` : rang numérique de la phrase (int | None)
      - `ordinal_phrase` : ordinal normalisé selon la règle du Sénat p. 26 (str | None)
      - `ordinal_recevable` : bool indiquant le respect de la règle des 2 / 3 / 5 composants du Sénat
      - `occurrence_mots` : nombre ou rang d'occurrence de mots (int | None)
      - `occurrence_mention` : mention textuelle de l'occurrence (str | None)
    """
    chapeau_brut = extraire_chapeau_brut(texte)
    chapeau_masque = _masquer_citations(chapeau_brut)

    verbe, verbe_cardinal = _extraire_verbe_cardinal(chapeau_masque, chapeau_brut)
    alinea_num, alinea_fin, alineas_vises = _extraire_alinea_num(chapeau_masque)
    rang_phrase, ordinal_phrase, ordinal_recevable, motif_ordinal = _extraire_rang_phrase(
        chapeau_masque, nb_composants=nb_composants
    )
    occurrence_mots, occurrence_mention = _extraire_occurrence_mots(chapeau_masque)
    cible_type = _determiner_cible_type(chapeau_masque, verbe, alinea_num, rang_phrase)
    audit_normatif = detecter_dispositions_non_normatives(texte)

    return ChapeauAnalysis(
        chapeau_brut=chapeau_brut,
        verbe=verbe,
        verbe_action=verbe,
        verbe_cardinal=verbe_cardinal,
        cible_type=cible_type,
        alinea_num=alinea_num,
        alinea_fin=alinea_fin,
        alineas_vises=alineas_vises,
        rang_phrase=rang_phrase,
        ordinal_phrase=ordinal_phrase,
        ordinal_recevable=ordinal_recevable,
        motif_ordinal=motif_ordinal,
        occurrence_mots=occurrence_mots,
        occurrence_mention=occurrence_mention,
        alerte_non_normatif=audit_normatif["alerte_non_normatif"],
        motif_non_normatif=audit_normatif["motif_non_normatif"],
        formules_non_normatives=audit_normatif["formules_detectees"],
    )


analyser_chapeau = parse_chapeau


# ──────────────────────────────────────────────────────────────────────────
# CHANTIER 2 : Calculateur d'ordre au Dérouleur de séance
# ──────────────────────────────────────────────────────────────────────────

def _extraire_infos_amendement(amendement: Any) -> tuple[str, str, Optional[int]]:
    """
    Extrait (dispositif, article_vise, alinea_explicite) depuis une chaîne, un dict ou un EnrichedAmendment.
    """
    if isinstance(amendement, str):
        return (amendement, "", None)

    if isinstance(amendement, dict):
        am = amendement.get("amendement", amendement)
        disp = (
            am.get("dispositif_raw")
            or am.get("dispositif")
            or am.get("texte")
            or am.get("dispositif_clean")
            or ""
        )
        if isinstance(disp, dict):
            disp = ""
        if not disp and isinstance(am.get("corps"), dict):
            disp = am["corps"].get("contenuAuteur", {}).get("dispositif") or am["corps"].get("dispositif") or ""
        art = (
            am.get("article_vise")
            or am.get("article")
            or am.get("pointeurFragmentTexte", {}).get("division", {}).get("articleDesignationCourte")
            or am.get("pointeurFragmentTexte", {}).get("division", {}).get("titre")
            or ""
        )
        al_raw = am.get("alinea_vise") or am.get("alinea_num")
        al_int = None
        if al_raw is not None and str(al_raw).strip().isdigit():
            al_int = int(str(al_raw).strip())
        return (str(disp), str(art), al_int)

    # Objet Pydantic EnrichedAmendment ou similaire
    disp = getattr(amendement, "dispositif_raw", "") or getattr(amendement, "dispositif_clean", "") or getattr(amendement, "dispositif", "") or ""
    art = getattr(amendement, "article_vise", "") or getattr(amendement, "article", "") or ""
    al_raw = getattr(amendement, "alinea_vise", None) or getattr(amendement, "alinea_num", None)
    al_int = None
    if al_raw is not None and str(al_raw).strip().isdigit():
        al_int = int(str(al_raw).strip())
    return (str(disp), str(art), al_int)


_SOUS_PRIORITE_VERBE: dict[str, int] = {
    VerbeAction.SUPPRIMER.value: 1,
    VerbeAction.REDIGER_AINSI.value: 2,
    VerbeAction.RETABLIR.value: 2,
    VerbeAction.REMPLACER.value: 3,
    VerbeAction.SUBSTITUER.value: 3,
    VerbeAction.AJOUTER.value: 4,
    VerbeAction.INSERER.value: 4,
    VerbeAction.COMPLETER.value: 5,
}


def calculer_priorite_derouleur(amendement: Any) -> tuple[int, int, int, int, str]:
    """
    Détermine l'ordre officiel de discussion en séance publique au Dérouleur sur un article donné :
      - Priorité 10 : Amendements de suppression totale de l'article (`SUPPRIMER cet article`).
      - Priorité 20 : Amendements de rédaction globale de l'article (`REDIGER_AINSI cet article`).
      - Priorité 30 + (alinea_num * 10) + rang_phrase : Amendements modifiant le corps de l'article,
        appelés strictement de l'alinéa 1 au dernier alinéa, puis de la première phrase à la dernière phrase.
      - Priorité 800 : Amendements complétant l'article in fine (`COMPLETER cet article`).
      - Priorité 900 : Amendements portant article additionnel (`APRÈS L'ARTICLE X, insérer l'article suivant :`).
      - Cas des Identiques : À priorité égale, les amendements ayant un texte identique partagent
        exactement le même tuple de priorité (même rang d'appel) pour être débattus et votés simultanément.

    Returns:
        tuple: `(priorite_derouleur, alinea_effectif, rang_phrase_effectif, sous_priorite_verbe, empreinte_identique)`
    """
    dispositif, article_vise, alinea_explicite = _extraire_infos_amendement(amendement)
    analyse = parse_chapeau(dispositif)

    chapeau_norm = _deaccent(analyse.chapeau_brut).lower()
    art_norm = _deaccent(article_vise).lower()
    empreinte = _fingerprint_text(dispositif)

    verbe = analyse.verbe
    alinea_num = analyse.alinea_num if analyse.alinea_num is not None else alinea_explicite
    rang_phrase = analyse.rang_phrase if analyse.rang_phrase is not None else 0
    sous_prio = _SOUS_PRIORITE_VERBE.get(verbe, 5)

    # ── 1. Priorité 900 : Amendements portant article additionnel ──
    is_article_additionnel = (
        bool(re.search(r"\b(?:apres|avant)\s+l['’\s]*article\b", chapeau_norm))
        or bool(re.search(r"\barticle\s+additionnel\b", chapeau_norm))
        or bool(re.search(r"\binserer\s+(?:l['’\s]*article\s+suivant|un\s+article)\b", chapeau_norm))
        or bool(re.search(r"\b(?:apres|avant)\s+(?:l['’\s]*article|art\b)", art_norm))
        or "additionnel" in art_norm
    )
    if is_article_additionnel:
        return (900, 999, 0, sous_prio, empreinte)

    # Est-ce une modification partielle du début ou de la fin de l'article ?
    is_debut_ou_fin = bool(re.search(r"\b(?:le\s+debut|au\s+debut|la\s+fin)\b", chapeau_norm))

    # ── 2. Priorité 10 : Suppression totale de l'article ──
    if (
        verbe == VerbeAction.SUPPRIMER.value
        and analyse.cible_type == CibleType.ARTICLE.value
        and alinea_num is None
        and rang_phrase == 0
        and not is_debut_ou_fin
    ) or bool(re.search(r"\b(?:supprimer\s+(?:cet\s+article|l['’\s]*article)|cet\s+article\s+est\s+supprime|l['’\s]*article\s+(?:premier|1er|unique|\d+)\s+est\s+supprime)\b", chapeau_norm)):
        if alinea_num is None and not is_debut_ou_fin:
            return (10, 0, 0, 1, empreinte)

    # ── 3. Priorité 20 : Rédaction globale de l'article (ou rétablissement global de l'article) ──
    if (
        verbe in (VerbeAction.REDIGER_AINSI.value, VerbeAction.RETABLIR.value)
        and analyse.cible_type == CibleType.ARTICLE.value
        and alinea_num is None
        and rang_phrase == 0
        and not is_debut_ou_fin
    ):
        return (20, 0, 0, 2, empreinte)

    # ── 4. Priorité 800 : Amendements complétant l'article in fine (`COMPLETER cet article`) ──
    if (
        verbe == VerbeAction.COMPLETER.value
        and alinea_num is None
        and rang_phrase == 0
        and (
            analyse.cible_type == CibleType.ARTICLE.value
            or bool(re.search(r"\bcompleter\s+(?:cet\s+article|l['’\s]*article|l['’\s]*alinea\s+unique)\b", chapeau_norm))
        )
    ):
        return (800, 999, 0, 5, empreinte)

    # ── 5. Priorité 30 + (alinea_num * 10) + rang_phrase : Corps de l'article ──
    if alinea_num is None:
        # Si l'amendement vise « Au début » de l'article sans numéro d'alinéa : alinea_eff = 0 -> priorité 30
        if re.search(r"\bau\s+debut\b", chapeau_norm):
            alinea_eff = 0
        else:
            # Article à alinéa unique (AN p. 7) : implicite sur l'alinéa 1
            alinea_eff = 1
    else:
        alinea_eff = alinea_num

    priorite_corps = 30 + (alinea_eff * 10) + rang_phrase
    return (priorite_corps, alinea_eff, rang_phrase, sous_prio, empreinte)


def ordonner_au_derouleur(amendements: list[Any]) -> list[dict[str, Any]]:
    """
    Trie une liste d'amendements selon l'ordre officiel du Dérouleur de séance et
    attribue à chacun son `rang_appel`.
    Les amendements identiques (même priorité et même empreinte textuelle) partagent
    strictement le même `rang_appel` pour être débattus et votés simultanément.
    """
    items = []
    for idx, am in enumerate(amendements):
        cle = calculer_priorite_derouleur(am)
        items.append({"amendement": am, "priorite_tuple": cle, "priorite": cle[0], "index_initial": idx})

    items.sort(key=lambda x: (x["priorite_tuple"], x["index_initial"]))

    rang_courant = 0
    precedente_cle: Optional[tuple] = None
    for item in items:
        if item["priorite_tuple"] != precedente_cle:
            rang_courant += 1
            precedente_cle = item["priorite_tuple"]
        item["rang_appel"] = rang_courant

    return items


# ──────────────────────────────────────────────────────────────────────────
# CHANTIER 3 : Auditeur constitutionnel de gage (Article 40)
# ──────────────────────────────────────────────────────────────────────────

# 1. Termes clés déclenchant une suspicion de perte de recettes ou création de charge
_TERMES_RISQUE_ART40: list[tuple[str, re.Pattern]] = [
    ("crédit d'impôt", re.compile(r"\bcr[eé]dits?\s+d['’\s]*imp[oô]ts?\b", re.IGNORECASE)),
    ("exonération", re.compile(r"\bexon[eé]rations?\b|\bexon[eé]r[eé]e?s?\b", re.IGNORECASE)),
    ("déduction", re.compile(r"\bd[eé]ductions?\b", re.IGNORECASE)),
    ("abattement", re.compile(r"\babattements?\b", re.IGNORECASE)),
    ("taux réduit", re.compile(r"\btaux\s+r[eé]duits?\b", re.IGNORECASE)),
    ("remboursement", re.compile(r"\bremboursements?\b", re.IGNORECASE)),
    ("prise en charge par l'État", re.compile(r"\bprise\s+en\s+charge\s+par\s+l['’\s]*[eé]tat\b", re.IGNORECASE)),
    ("compensation", re.compile(r"\bcompensations?\b", re.IGNORECASE)),
]

# 2. Les 4 formules sacramentelles de gages obligatoires (AN p. 14-16, Sénat p. 60-65)
_GAGES_OFFICIELS: list[tuple[str, re.Pattern]] = [
    (
        "Gage Tabac (État)",
        re.compile(
            r"taxe\s+additionnelle\s+aux\s+droits\s+(?:pr[eé]vus|vis[eé]s)\s+aux\s+articles\s+575\s+et\s+575\s*a\s+du\s+code\s+g[eé]n[eé]ral\s+des\s+imp[oô]ts|"
            r"taxe\s+additionnelle\s+[aà]\s+l['’\s]*accise\s+sur\s+les\s+tabacs\s+(?:pr[eé]vue|vis[eé]e)\s+au\s+chapitre\s+iv\s+du\s+titre\s+(?:ier|1er|i\s*er)\s+du\s+livre\s+iii\s+du\s+code\s+des\s+impositions\s+sur\s+les\s+biens\s+et\s+services",
            re.IGNORECASE,
        ),
    ),
    (
        "Gage Alcool (État)",
        re.compile(
            r"taxe\s+additionnelle\s+au\s+droit\s+(?:pr[eé]vu|vis[eé])\s+[aà]\s+l['’\s]*article\s+403\s+du\s+code\s+g[eé]n[eé]ral\s+des\s+imp[oô]ts",
            re.IGNORECASE,
        ),
    ),
    (
        "Gage Collectivités territoriales (DGF)",
        re.compile(
            r"majoration\s+(?:[aà]\s+due\s+concurrence\s+)?de\s+la\s+dotation\s+globale\s+de\s+fonctionnement(?:\s*\(\s*dgf\s*\))?",
            re.IGNORECASE,
        ),
    ),
    (
        "Gage Sécurité sociale",
        re.compile(
            r"contribution\s+additionnelle\s+[aà]\s+la\s+contribution\s+(?:pr[eé]vue|vis[eé]e)\s+[aà]\s+l['’\s]*article\s+l\.?\s*136[\s\-–—]*7[\s\-–—]*1\s+du\s+code\s+de\s+la\s+s[eé]curit[eé]\s+sociale",
            re.IGNORECASE,
        ),
    ),
]

# Règle spécifique Crédit d'impôt (Sénat p. 65)
_CLAUSE_CREDIT_IMPOT_RE = re.compile(
    r"ne\s+s['’\s]*applique\s+qu['’\s]*aux\s+sommes\s+venant\s+en\s+d[eé]duction\s+de\s+l['’\s]*imp[oô]t\s+d[uû]",
    re.IGNORECASE,
)


def auditer_recevabilite_art40(dispositif: Any, raw_dict: Optional[dict] = None) -> dict[str, Any]:
    """
    Audite un dispositif d'amendement au titre de l'Article 40 de la Constitution
    (AN p. 14-16, Sénat p. 60-65).

    1. Détecte les termes de risque financier (« crédit d'impôt », « exonération »,
       « déduction », « abattement », « taux réduit », « remboursement »,
       « prise en charge par l'État », « compensation »).
    2. Détecte dans les paragraphes finaux du dispositif les 4 formules sacramentelles de gages :
       - Gage Tabac (État) : CGI art. 575 et 575 A OU CIBS livre III titre Ier chapitre IV
       - Gage Alcool (État) : CGI art. 403
       - Gage Collectivités territoriales : majoration à due concurrence de la DGF
       - Gage Sécurité sociale : CSS art. L. 136-7-1
    3. Vérifie la règle spécifique Sénat (p. 65) sur les crédits d'impôt :
       présence obligatoire de la clause « ne s'applique qu'aux sommes venant en déduction de l'impôt dû ».

    Returns:
        dict contenant :
          - `alerte_recevabilite_art40` (bool)
          - `motif_art40` (str | None)
          - `gage_detecte` (str | None)
          - `termes_risque` (list[str])
          - `clause_credit_impot_presente` (bool)
    """
    clean = _strip_html(dispositif)
    if not clean:
        return {
            "alerte_recevabilite_art40": False,
            "motif_art40": None,
            "gage_detecte": None,
            "termes_risque": [],
            "clause_credit_impot_presente": False,
        }

    # Normalisation des espaces et apostrophes pour les regex
    texte_unifie = re.sub(r"\s+", " ", clean)

    # 1. Recherche des gages officiels dans le dispositif
    gages_trouves: list[str] = []
    for label_gage, pattern_gage in _GAGES_OFFICIELS:
        if pattern_gage.search(texte_unifie):
            gages_trouves.append(label_gage)

    # Vérification de la clause spéciale crédit d'impôt (Sénat p. 65)
    has_clause_credit_impot = bool(_CLAUSE_CREDIT_IMPOT_RE.search(texte_unifie))

    # Pour analyser les termes de risque dans le dispositif normatif sans faux positif
    # sur la clause « venant en déduction de l'impôt dû » elle-même :
    texte_sans_clause_gage = _CLAUSE_CREDIT_IMPOT_RE.sub(" ", texte_unifie)
    texte_sans_clause_gage = re.sub(
        r"pour\s+compenser\s+la\s+perte\s+de\s+recettes[^.]*\.",
        " ",
        texte_sans_clause_gage,
        flags=re.IGNORECASE,
    )
    texte_sans_clause_gage = re.sub(
        r"la\s+perte\s+de\s+recettes\s+r[eé]sultant[^.]*\.",
        " ",
        texte_sans_clause_gage,
        flags=re.IGNORECASE,
    )

    termes_detectes: list[str] = []
    for label_terme, pattern_terme in _TERMES_RISQUE_ART40:
        if pattern_terme.search(texte_sans_clause_gage):
            termes_detectes.append(label_terme)

    gage_str = " + ".join(gages_trouves) if gages_trouves else None
    has_credit_impot = "crédit d'impôt" in termes_detectes

    # Cas 1 : Aucun risque détecté
    if not termes_detectes:
        return {
            "alerte_recevabilite_art40": False,
            "motif_art40": None,
            "gage_detecte": gage_str,
            "termes_risque": [],
            "clause_credit_impot_presente": has_clause_credit_impot,
        }

    # Cas 2 : Risque financier détecté mais AUCUN gage valide
    if not gages_trouves:
        termes_fmt = ", ".join(f"« {t} »" for t in termes_detectes)
        precision_ci = (
            " En outre, s'agissant d'un crédit d'impôt (Sénat p. 65), le dispositif doit "
            "impérativement inclure la clause « ne s'applique qu'aux sommes venant en déduction de l'impôt dû »."
            if has_credit_impot and not has_clause_credit_impot
            else ""
        )
        return {
            "alerte_recevabilite_art40": True,
            "motif_art40": (
                f"Risque d'irrecevabilité financière au titre de l'Article 40 de la Constitution : "
                f"diminution de ressources publiques ou création de charge détectée ({termes_fmt}) "
                f"sans formule de gage constitutionnel valide en fin de dispositif.{precision_ci}"
            ),
            "gage_detecte": None,
            "termes_risque": termes_detectes,
            "clause_credit_impot_presente": has_clause_credit_impot,
        }

    # Cas 3 : Crédit d'impôt avec gage fiscal, mais SANS la clause impérative Sénat p. 65
    if has_credit_impot and not has_clause_credit_impot:
        return {
            "alerte_recevabilite_art40": True,
            "motif_art40": (
                "Risque d'irrecevabilité Art. 40 sur crédit d'impôt (Sénat p. 65) : "
                "malgré la présence d'un gage, il manque la clause impérative indiquant que "
                "le dispositif « ne s'applique qu'aux sommes venant en déduction de l'impôt dû »."
            ),
            "gage_detecte": gage_str,
            "termes_risque": termes_detectes,
            "clause_credit_impot_presente": False,
        }

    # Cas 4 : Risque financier dûment couvert par un gage constitutionnel valide
    return {
        "alerte_recevabilite_art40": False,
        "motif_art40": None,
        "gage_detecte": gage_str,
        "termes_risque": termes_detectes,
        "clause_credit_impot_presente": has_clause_credit_impot,
    }


# ──────────────────────────────────────────────────────────────────────────
# CHANTIER 4 : Détecteur de dispositions non normatives (Guide de légistique SGG / CE)
# ──────────────────────────────────────────────────────────────────────────

MOTIF_NON_NORMATIF_DEFAUT = (
    "Dispositif à faible portée normative (risque de censure pour défaut de normativité, Art. 6 DDHC)."
)

_FORMULES_NON_NORMATIVES: list[tuple[str, re.Pattern]] = [
    ("a pour objectif de", re.compile(r"\b(?:a|ont)\s+pour\s+objectifs?\s+d(?:e\b|['’])", re.IGNORECASE)),
    ("favorise par son action", re.compile(r"\bfavorise(?:nt)?\s+par\s+(?:son|leur)\s+action\b", re.IGNORECASE)),
    ("veille à ce que", re.compile(r"\bveille(?:nt)?\s+[aà]\s+ce\s+qu(?:e\b|['’])", re.IGNORECASE)),
    ("la Nation reconnaît", re.compile(r"\bla\s+nation\s+reconna[iî]t\b", re.IGNORECASE)),
    ("se donne pour mission de", re.compile(r"\bse\s+donne(?:nt)?\s+pour\s+missions?\s+d(?:e\b|['’])", re.IGNORECASE)),
    (
        "encourage les initiatives visant à",
        re.compile(r"\bencourage(?:nt)?\s+les\s+initiatives\s+visant\s+[aà]\b", re.IGNORECASE),
    ),
    ("a vocation à", re.compile(r"\b(?:a|ont)\s+vocation\s+[aà]\b", re.IGNORECASE)),
]


def detecter_dispositions_non_normatives(dispositif: Any) -> dict[str, Any]:
    """
    Détecte les dispositions dépourvues de portée normative (« neutrons législatifs »)
    au sens du Guide de légistique (fiches 1.1.1 et 1.2.1) et de la jurisprudence du
    Conseil constitutionnel (décisions n° 2004-500 DC et 2005-512 DC, Art. 6 DDHC).

    Returns:
        dict contenant :
          - `alerte_non_normatif` (bool)
          - `motif_non_normatif` (str | None)
          - `formules_detectees` (list[str])
    """
    clean = _strip_html(dispositif)
    if not clean:
        return {
            "alerte_non_normatif": False,
            "motif_non_normatif": None,
            "formules_detectees": [],
        }

    texte_unifie = re.sub(r"\s+", " ", clean)
    formules_trouvees: list[str] = []
    for label, pattern in _FORMULES_NON_NORMATIVES:
        if pattern.search(texte_unifie):
            formules_trouvees.append(label)

    if formules_trouvees:
        return {
            "alerte_non_normatif": True,
            "motif_non_normatif": MOTIF_NON_NORMATIF_DEFAUT,
            "formules_detectees": formules_trouvees,
        }

    return {
        "alerte_non_normatif": False,
        "motif_non_normatif": None,
        "formules_detectees": [],
    }


auditer_portee_normative = detecter_dispositions_non_normatives
detecter_non_normatif = detecter_dispositions_non_normatives


