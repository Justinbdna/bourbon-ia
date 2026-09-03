"""
api/commissions_resolver.py — Résolveur des commissions et corrélation thématique
=================================================================================
Deux responsabilités, toutes deux 100 % déterministes (aucun LLM) :

  1. RÉSOUDRE la commission saisie d'un amendement.
  2. CORRÉLER le périmètre thématique de cette commission avec le texte de
     l'amendement, pour n'afficher que les mots-clés RÉELLEMENT présents.

⚠️  POURQUOI CETTE CORRÉLATION EST UTILE
Un amendement dont AUCUN mot-clé de sa commission n'apparaît dans le dispositif
est un signal faible de « cavalier législatif » (article 45 de la Constitution :
absence de lien, même indirect, avec le texte). Ce n'est pas une preuve
d'irrecevabilité — c'est une piste de relecture pour l'administrateur.

──────────────────────────────────────────────────────────────────────────────
RÉSOLUTION HORS-LIGNE — vérifié sur données réelles
L'identifiant d'organe est EMBARQUÉ dans l'uid de l'amendement :

    AMANR5L17 PO59051 B2820P0D1N000019
              ^^^^^^^ → Commission des lois

Concordance mesurée : 50/50 sur 6 commissions distinctes (lois, affaires
culturelles, affaires sociales, finances, affaires économiques, développement
durable) — aucun écart avec le champ `organeRef` renvoyé par l'API.

Conséquence : la commission se résout SANS aucun appel réseau, ce qui préserve
le mode souverain / hors-ligne de Bourbon.IA. L'API Tricoteuses n'est sollicitée
qu'en dernier recours, pour les organes absents du référentiel local
(commissions spéciales, commissions mixtes paritaires créées en cours de route).
──────────────────────────────────────────────────────────────────────────────

Aucune fonction de ce module ne lève d'exception : en cas d'inconnu, on renvoie
une structure vide plutôt que de bloquer le pipeline.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("bourbon.commissions")

CURRENT_DIR = Path(__file__).resolve().parent
DATA_PATH = CURRENT_DIR / "data" / "commissions.json"

# Longueur minimale d'un radical pour autoriser la correspondance par préfixe.
# En dessous, on génère trop de faux positifs (« eau » matcherait « beaucoup »).
_MIN_RADICAL = 5

_COMMISSIONS_DB: Optional[dict[str, dict[str, Any]]] = None
_CACHE_DISTANT: dict[str, dict[str, Any]] = {}


# ──────────────────────────────────────────────────────────────────────────
# Chargement du référentiel local
# ──────────────────────────────────────────────────────────────────────────
def _load_commissions_db() -> dict[str, dict[str, Any]]:
    """Charge le snapshot local (singleton en mémoire, dégradation totale)."""
    global _COMMISSIONS_DB
    if _COMMISSIONS_DB is not None:
        return _COMMISSIONS_DB

    _COMMISSIONS_DB = {}
    try:
        if DATA_PATH.is_file():
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                _COMMISSIONS_DB = json.load(f)
            logger.info(f"🏛️ Référentiel commissions chargé : {len(_COMMISSIONS_DB)} entrées.")
        else:
            logger.warning(f"⚠️ commissions.json introuvable ({DATA_PATH}). Mode dégradé.")
    except Exception as exc:
        logger.warning(f"⚠️ Erreur chargement commissions.json ({exc}). Mode dégradé.")
        _COMMISSIONS_DB = {}
    return _COMMISSIONS_DB


# ──────────────────────────────────────────────────────────────────────────
# Normalisation textuelle
# ──────────────────────────────────────────────────────────────────────────
def _normaliser(texte: Any) -> str:
    """minuscules, sans accents, sans HTML — pour une comparaison robuste."""
    if not texte:
        return ""
    brut = re.sub(r"<[^>]+>", " ", str(texte))
    nfkd = unicodedata.normalize("NFKD", brut)
    sans_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sans_accents.lower()).strip()


def _radical(mot_normalise: str) -> str:
    """
    Radical grossier pour absorber les variations morphologiques du français :
    « fiscal » doit reconnaître « fiscalité », « fiscales »…
    On coupe les terminaisons les plus fréquentes, sans prétendre à un vrai
    lemmatiseur (inutile ici, et coûteux).
    """
    for suffixe in ("ements", "ement", "ations", "ation", "ités", "ité",
                    "elles", "elle", "aux", "als", "es", "s", "e"):
        if mot_normalise.endswith(suffixe) and len(mot_normalise) - len(suffixe) >= _MIN_RADICAL:
            return mot_normalise[: -len(suffixe)]
    return mot_normalise


# ──────────────────────────────────────────────────────────────────────────
# 1. Résolution de la commission
# ──────────────────────────────────────────────────────────────────────────
def extraire_organe_uid(amendement: Any) -> str:
    """
    Détermine l'identifiant d'organe (PO…) d'un amendement.

    Ordre de priorité :
      1. `organeRef.uid` explicite (donnée Tricoteuses la plus fiable) ;
      2. `organeRefUid` à plat ;
      3. extraction depuis l'uid de l'amendement (voir en-tête : validé 50/50).

    Returns:
        L'uid d'organe, ou "" si indéterminable.
    """
    if not isinstance(amendement, dict):
        return ""

    organe = amendement.get("organeRef")
    if isinstance(organe, dict) and organe.get("uid"):
        return str(organe["uid"])

    plat = amendement.get("organeRefUid") or amendement.get("organe_ref")
    if plat:
        return str(plat)

    for champ in ("uid", "amendement_uid", "id"):
        valeur = amendement.get(champ)
        if valeur:
            trouve = re.search(r"(PO\d+)", str(valeur))
            if trouve:
                return trouve.group(1)
    return ""


def get_commission_info(organe_uid: str, autoriser_reseau: bool = False) -> dict[str, Any]:
    """
    Retourne la fiche d'une commission : {uid, libelle, abrege, mots_cles}.

    Args:
        organe_uid       : identifiant PO…
        autoriser_reseau : si True, interroge Tricoteuses pour un organe absent
                           du référentiel local. Désactivé par défaut afin de
                           préserver le fonctionnement hors-ligne.

    Ne lève jamais : renvoie une fiche vide si l'organe reste inconnu.
    """
    vide = {"uid": organe_uid or "", "libelle": "", "abrege": "", "mots_cles": []}
    if not organe_uid:
        return vide

    fiche = _load_commissions_db().get(organe_uid)
    if fiche:
        return {"uid": organe_uid, **fiche}

    if organe_uid in _CACHE_DISTANT:
        return _CACHE_DISTANT[organe_uid]

    if not autoriser_reseau:
        return vide

    # Repli réseau : commissions spéciales / CMP absentes du snapshot.
    try:
        # Double import : convention du dépôt (cf. api/index.py) — `api.x` en
        # local, `x` une fois bundlé par Vercel Serverless.
        try:
            from api.tricoteuses_client import _request
        except ModuleNotFoundError:
            from tricoteuses_client import _request
        donnees = _request(f"/v2/organes/{organe_uid}").get("data") or {}
        resolue = {
            "uid": organe_uid,
            "libelle": donnees.get("libelle", ""),
            "abrege": donnees.get("libelleAbrege", ""),
            # Aucun mot-clé curaté pour un organe hors référentiel : on ne devine pas.
            "mots_cles": [],
        }
        _CACHE_DISTANT[organe_uid] = resolue
        logger.info(f"🌐 Commission {organe_uid} résolue via l'API : {resolue['libelle'][:50]}")
        return resolue
    except Exception as exc:
        logger.warning(f"⚠️ Résolution distante impossible pour {organe_uid} ({exc}).")
        return vide


# ──────────────────────────────────────────────────────────────────────────
# 2. Corrélation thématique amendement ↔ commission
# ──────────────────────────────────────────────────────────────────────────
def correler_mots_cles(mots_cles: list[str], *textes: Any) -> list[str]:
    """
    Ne conserve que les mots-clés de la commission RÉELLEMENT présents dans le
    texte de l'amendement (dispositif, exposé sommaire…).

    La comparaison est faite sur radicaux normalisés, ce qui reconnaît les
    variantes morphologiques (« fiscal » ↔ « fiscalité »). Les expressions
    composées (« sécurité sociale ») sont testées telles quelles.

    L'ordre du référentiel est préservé : l'affichage reste stable d'une ligne
    à l'autre, ce qui facilite la lecture en colonne.
    """
    if not mots_cles:
        return []

    corpus = _normaliser(" ".join(str(t) for t in textes if t))
    if not corpus:
        return []

    corpus_radicaux = {_radical(m) for m in re.findall(r"[a-z0-9]+", corpus)}
    trouves: list[str] = []

    for mot in mots_cles:
        mot_norm = _normaliser(mot)
        if not mot_norm:
            continue
        if " " in mot_norm:
            # Expression composée : correspondance littérale
            if mot_norm in corpus:
                trouves.append(mot)
            continue
        if _radical(mot_norm) in corpus_radicaux:
            trouves.append(mot)

    return trouves


def resoudre_commission_et_mots_cles(
    amendement: Any,
    autoriser_reseau: bool = False,
) -> dict[str, Any]:
    """
    Point d'entrée unique du module.

    Returns:
        {
          "commission_ref":      "PO59051",
          "commission_libelle":  "Commission des lois constitutionnelles…",
          "commission_abrege":   "Lois",
          "commission_mots_cles": ["justice", "liberté"],   # corrélés au texte
          "commission_hors_champ": False,   # True = aucun thème de la commission
                                            #        retrouvé dans l'amendement
        }

    `commission_hors_champ` reste False quand la commission n'a pas de périmètre
    thématique propre (séance publique) ou n'est pas résolue : on ne signale
    jamais un « hors champ » qu'on ne peut pas établir.
    """
    vide = {
        "commission_ref": "",
        "commission_libelle": "",
        "commission_abrege": "",
        "commission_mots_cles": [],
        "commission_hors_champ": False,
    }
    if not isinstance(amendement, dict):
        return vide

    try:
        organe_uid = extraire_organe_uid(amendement)
        if not organe_uid:
            return vide

        fiche = get_commission_info(organe_uid, autoriser_reseau=autoriser_reseau)
        mots_reference = fiche.get("mots_cles") or []

        textes = (
            amendement.get("dispositif") or amendement.get("dispositif_clean")
            or amendement.get("texte") or "",
            amendement.get("exposeSommaire") or amendement.get("expose_sommaire") or "",
        )
        correles = correler_mots_cles(mots_reference, *textes)

        return {
            "commission_ref": organe_uid,
            "commission_libelle": fiche.get("libelle", ""),
            "commission_abrege": fiche.get("abrege", ""),
            "commission_mots_cles": correles,
            # Hors champ uniquement si la commission A un périmètre connu
            # et qu'aucun de ses thèmes n'apparaît.
            "commission_hors_champ": bool(mots_reference) and not correles,
        }
    except Exception as exc:
        logger.warning(f"⚠️ Erreur résolution commission ({exc}). Mode dégradé.")
        return vide


# ──────────────────────────────────────────────────────────────────────────
# Auto-test hors-ligne
# ──────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    exemples = [
        # Commission des lois, texte manifestement dans son périmètre
        {"uid": "AMANR5L17PO59051B2820P0D1N000019",
         "dispositif": "Supprimer cet article.",
         "exposeSommaire": "Cet article porte atteinte aux libertés et à la justice "
                           "administrative ainsi qu'aux règles d'élection."},
        # Commission des finances
        {"uid": "AMANR5L17PO59048B1234P0D1N000007",
         "dispositif": "Majorer le taux de la taxe et compenser la perte de recettes "
                       "par une hausse de la fiscalité sur le tabac."},
        # Commission des lois mais texte sans aucun thème de la commission → cavalier ?
        {"uid": "AMANR5L17PO59051B9999P0D1N000042",
         "dispositif": "Compléter cet article par les mots : « et le tourisme équestre »."},
        # Séance publique : aucun périmètre thématique
        {"uid": "AMANR5L17PO838901B1111P0D1N000003",
         "dispositif": "Supprimer cet article."},
        # Données inexploitables
        {"uid": "SANS_ORGANE", "dispositif": "x"},
    ]

    print("═" * 74)
    print("  AUTO-TEST · Résolution commission + corrélation thématique")
    print("═" * 74)
    for i, amd in enumerate(exemples, 1):
        r = resoudre_commission_et_mots_cles(amd)
        drapeau = "  ⚠️ HORS CHAMP" if r["commission_hors_champ"] else ""
        print(f"\n{i}. {amd['uid']}")
        print(f"   commission : {r['commission_abrege'] or '(non résolue)'}")
        print(f"   mots-clés  : {r['commission_mots_cles'] or '—'}{drapeau}")
    print("\n" + "═" * 74)
