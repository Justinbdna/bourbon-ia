"""
tests/test_mcp_server.py — Tests unitaires du Serveur MCP Souverain (`api/mcp_server.py`)
=====================================================================================
Vérifie :
  1. L'enregistrement des 4 outils MCP (`classer_liasse_mecanique`, `inspecter_amendement`,
     `rechercher_sources_rag`, `generer_prejaune_rtf`).
  2. L'exécution nominale de `classer_liasse_mecanique` (détection d'identiques `[Id.]` et statistiques).
  3. L'exécution nominale de `inspecter_amendement` (alertes Art. 40 / Art. 98 et concurrents de division).
  4. L'exécution nominale de `rechercher_sources_rag` (citations exactes et repli strict
     `"Information non disponible dans les sources"`).
  5. La génération RTF via `generer_prejaune_rtf`.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import api.mcp_server as mcp_server
from api.services.rag_store import STRICT_NO_SOURCE_MESSAGE, PersistentRAGStore

LIASSE_EXEMPLE = [
    {
        "uid": "AM-TEST-1",
        "identification": {"numeroLong": "10", "numeroOrdreDepot": 10},
        "pointeurFragmentTexte": {"division": {"titre": "Article 1er"}},
        "signataires": {
            "auteur": {"acteurRef": "PA720846", "groupePolitiqueRef": "PO845413"},
            "libelle": "M. Bastien Lachaud",
        },
        "corps": {
            "contenuAuteur": {
                "dispositif": "<p>Supprimer cet article.</p>",
                "exposeSommaire": "<p>Suppression de l'article premier.</p>",
            }
        },
    },
    {
        "uid": "AM-TEST-2",
        "identification": {"numeroLong": "11", "numeroOrdreDepot": 11},
        "pointeurFragmentTexte": {"division": {"titre": "Article 1er"}},
        "signataires": {
            "auteur": {"acteurRef": "PA840817", "groupePolitiqueRef": "PO845485"},
            "libelle": "M. Joël Bruneau",
        },
        "corps": {
            "contenuAuteur": {
                "dispositif": "<p>Supprimer cet article.</p>",
                "exposeSommaire": "<p>Même demande de suppression.</p>",
            }
        },
    },
    {
        "uid": "AM-TEST-3",
        "identification": {"numeroLong": "12", "numeroOrdreDepot": 12},
        "pointeurFragmentTexte": {"division": {"titre": "Article 1er"}},
        "signataires": {
            "auteur": {"acteurRef": "PA720846", "groupePolitiqueRef": "PO845413"},
            "libelle": "M. Bastien Lachaud",
        },
        "corps": {
            "contenuAuteur": {
                "dispositif": (
                    "<p>À l'alinéa 1, substituer aux mots : « deux ans » les mots : « cinq ans ».</p>"
                    "<p>La perte de recettes pour l'État est compensée à due concurrence par la création d'une taxe additionnelle aux droits mentionnés aux articles 575 et 575 A du code général des impôts.</p>"
                ),
                "exposeSommaire": "<p>Amendement gagé.</p>",
            }
        },
    },
]


def test_mcp_tools_registration():
    """Les 4 outils MCP requis doivent être enregistrés dans le serveur MCP."""
    registered_names = set(mcp_server.mcp.tools.keys())
    expected = {
        "classer_liasse_mecanique",
        "inspecter_amendement",
        "rechercher_sources_rag",
        "generer_prejaune_rtf",
    }
    assert expected.issubset(registered_names)


def test_mcp_classer_liasse_mecanique():
    """Vérifie le tri déterministe d'une liasse via l'outil MCP."""
    res = mcp_server.classer_liasse_mecanique(json.dumps(LIASSE_EXEMPLE))

    assert res["total"] == 3
    assert res["statistiques"].get("Identique", 0) >= 1
    assert len(res["groupes_identiques"]) == 1
    # Les amendements 10 (référent) et 11 (identique) sont regroupés sur l'Article 1er
    groupe_membres = next(iter(res["groupes_identiques"].values()))
    assert set(groupe_membres) == {"10", "11"}


def test_mcp_inspecter_amendement():
    """Vérifie l'inspection légistique, la détection de gage Art. 40 et l'alerte d'amendement tombant."""
    res = mcp_server.inspecter_amendement("AM-TEST-3", LIASSE_EXEMPLE)

    assert res["status"] == "ok"
    fiche = res["fiche_legistique"]
    alertes = res["alertes_recevabilite"]

    assert fiche["numero"] == "12"
    assert fiche["article"] == "Article 1er"
    assert alertes["est_gage_art40"] is True
    assert alertes["tombe_si_adoption"] is True
    assert len(res["concurrents_division"]) == 2


def test_mcp_rechercher_sources_rag(tmp_path: Path):
    """Vérifie la recherche RAG via MCP (source trouvée + repli strict sans hallucination)."""
    db_path = tmp_path / "mcp_rag.db"
    store = PersistentRAGStore(db_path=db_path)
    store.seed_default_corpus()

    hit = mcp_server.rechercher_sources_rag(
        "interdiction de toute forme de représailles lanceurs d'alerte",
        db_path=str(db_path),
    )
    assert hit["status"] == "ok"
    assert any(r["doc_id"] == "32019L1937" for r in hit["results"])

    miss = mcp_server.rechercher_sources_rag(
        "météorologie agricole en Nouvelle-Calédonie",
        db_path=str(db_path),
    )
    assert miss["status"] == "no_source"
    assert miss["answer"] == STRICT_NO_SOURCE_MESSAGE


def test_mcp_generer_prejaune_rtf():
    """Vérifie que l'outil MCP génère un document RTF valide contenant les crochets et mentions."""
    rtf = mcp_server.generer_prejaune_rtf(LIASSE_EXEMPLE)

    assert rtf.startswith("{\\rtf1\\ansi\\ansicpg1252\\deff0")
    assert "[Id.]" in rtf
    assert "Adt n" in rtf
