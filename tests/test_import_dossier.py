"""
tests/test_import_dossier.py — Import direct des amendements d'un dossier législatif
====================================================================================
L'API Tricoteuses est simulée : aucun appel réseau.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from api import import_dossier
from api.index import app, normaliser_amendement
from api.tricoteuses_client import TricoteusesError

client = TestClient(app)

# Amendement tel que renvoyé en liste par GET /v2/amendements (champs utiles).
AMENDEMENT_TRICOTEUSES = {
    "uid": "AMANR5L17PO419604B1641P0D1N000137",
    "numeroLong": "AC137",
    "acteurRefUid": None,
    "acteurRef": {"uid": "PA840817", "nom": "Bruneau", "prenom": "Joël"},
    "groupePolitiqueRef": {"uid": "PO845485", "libelle": "LIOT"},
    "typeAuteur": "Député",
    "dispositifHtml": "<p>Supprimer cet article.</p>",
    "exposeSommaireHtml": "<p>Article inutile.</p>",
    "divisionTitre": "Article 5",
    "divisionArticleDesignationCourte": "ART. 5",
    "divisionArticleDesignation": "ARTICLE 5",
    "alineaDesignation": None,
    "cartoucheInformatif": None,
    "etatLibelle": "Discuté",
    "sortAmendement": "Rejeté",
    "documentRef": {"uid": "PRJLANR5L17B1641"},
    "estIdentique": False,
    "idDiscussionIdentique": 85409,
    "amendementParentRefUid": None,
    "triAmendement": "abc",
}


def _faux_request(monkeypatch, totaux=None, donnees=None):
    """Simule _request : `totaux` par codeEtape, `donnees` renvoyées pour les amendements."""
    appels = []

    def faux(path, params=None, timeout=None):
        appels.append((path, dict(params or {})))
        if path == "/v2/dossiers":
            return {"data": [{"uid": "DLR5L17N52100", "titre": "Jeux 2030", "typeInitiative": "Projet de loi",
                              "statut": "Texte adopté", "dateDernierActe": "2026-03-20T00:00:00.000Z"}],
                    "pagination": {"total": 1}}
        total = (totaux or {}).get(params.get("codeEtape"), len(donnees or []))
        return {"data": list(donnees or []), "pagination": {"total": total}}

    monkeypatch.setattr(import_dossier, "_request", faux)
    monkeypatch.delenv("BOURBON_TEXTES_DISTANTS", raising=False)
    return appels


def test_conversion_au_format_an_puis_normalisation():
    an = import_dossier.tricoteuses_vers_format_an(AMENDEMENT_TRICOTEUSES)

    assert an["signataires"]["auteur"]["acteurRef"] == "PA840817"
    assert an["idDiscussionIdentique"] == "85409"
    assert an["texteLegislatifRef"] == "PRJLANR5L17B1641"

    norm = normaliser_amendement(an)
    assert norm["numero"] == "AC137"
    assert norm["article"] == "Article 5"
    assert norm["auteur"] == "Joël Bruneau (LIOT)"
    assert norm["dispositif"] == "Supprimer cet article."


def test_seance_pleniere_prend_les_themes_de_la_commission_au_fond():
    seance = dict(AMENDEMENT_TRICOTEUSES, uid="AMANR5L17PO838901BTC2233P0D1N000159",
                  exposeSommaireHtml="<p>Cet amendement protège le sport et les jeux olympiques.</p>")

    avec_fond = normaliser_amendement(import_dossier.tricoteuses_vers_format_an(seance, "PO419604"))
    sans_fond = normaliser_amendement(import_dossier.tricoteuses_vers_format_an(seance))

    assert avec_fond["commission"] == "Séance plénière · Affaires culturelles et éducation"
    assert "sport" in avec_fond["commission_mots_cles"]
    assert sans_fond["commission"] == "Séance plénière"
    assert sans_fond["commission_mots_cles"] == []


def test_liasses_ne_garde_que_les_etapes_avec_amendements(monkeypatch):
    _faux_request(monkeypatch, totaux={"AN1-COM": 341, "AN1-DEBATS": 329})

    r = client.get("/api/v2/dossiers/DLR5L17N52100/liasses")

    assert r.status_code == 200
    assert [(l["etape"], l["nb"]) for l in r.json()["liasses"]] == [("AN1-COM", 341), ("AN1-DEBATS", 329)]


def test_amendements_d_une_liasse(monkeypatch):
    appels = _faux_request(monkeypatch, donnees=[AMENDEMENT_TRICOTEUSES])

    r = client.get("/api/v2/dossiers/DLR5L17N52100/amendements", params={"etape": "AN1-COM"})

    assert r.status_code == 200
    corps = r.json()
    assert corps["total"] == 1 and corps["tronque"] is False
    assert corps["amendements"][0]["uid"] == AMENDEMENT_TRICOTEUSES["uid"]
    assert appels[0][1]["sort"] == "triAmendement.asc"


def test_liasse_tronquee_au_dela_de_la_limite(monkeypatch):
    _faux_request(monkeypatch, totaux={"AN1-DEBATS": 5000}, donnees=[AMENDEMENT_TRICOTEUSES])

    corps = import_dossier.amendements_de_liasse("DLR5L17N52100", "AN1-DEBATS")

    assert corps["total"] == 5000 and corps["tronque"] is True


def test_parametres_invalides_refuses():
    assert client.get("/api/v2/dossiers/PA1234/liasses").status_code == 400
    assert client.get("/api/v2/dossiers/DLR5L17N52100/amendements", params={"etape": "SN1-COM"}).status_code == 400


def test_mode_hors_ligne_et_api_injoignable(monkeypatch):
    monkeypatch.setenv("BOURBON_TEXTES_DISTANTS", "0")
    r = client.get("/api/v2/dossiers", params={"recherche": "jeux"})
    assert r.status_code == 503 and "hors-ligne" in r.json()["error"]

    def panne(path, params=None, timeout=None):
        raise TricoteusesError("Connexion impossible")

    monkeypatch.delenv("BOURBON_TEXTES_DISTANTS")
    monkeypatch.setattr(import_dossier, "_request", panne)
    r = client.get("/api/v2/dossiers", params={"recherche": "jeux"})
    assert r.status_code == 503 and "injoignables" in r.json()["error"]
