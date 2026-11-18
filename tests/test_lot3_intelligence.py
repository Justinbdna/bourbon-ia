"""
tests/test_lot3_intelligence.py — Tests unitaires et d'intégration du Lot 3
===========================================================================
Valide hors-ligne (0 appel réseau) :
  1. Détection des amendements tombants (`tombe_si_adoption_de`) et ordre d'appel Art. 98.
  2. Ingestion et évaluation des règles d'irrecevabilité (Art. 40, Art. 45 Cavalier législatif,
     Art. 98 RAN et catalogue extensible de 384 règles).
  3. Ingestion et croisement du graphe relationnel HATVP sur données tests.
  4. Debunker chronologique (cas avec contradiction détectée et cas `no_history` retournant
     strictement `"Information non disponible dans les sources"`).
  5. Soumission et suivi d'un job batch via `/api/v2/jobs/submit` et `/api/v2/jobs/{job_id}`,
     ainsi que les nouveaux outils MCP (`evaluer_regles_irrecevabilite`, `verifier_influence_hatvp`,
     `debunker_historique_acteur`).
"""

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import mcp_server
from api.index import app
from api.services.chrono_debunker import ChronoDebunkerStore
from api.services.deterministic_classifier import classer_par_regles
from api.services.hatvp_graph import HATVPGraphStore
from api.services.rag_store import STRICT_NO_SOURCE_MESSAGE, PersistentRAGStore
from api.services.rules_engine import LegislativeRulesEngine, compute_art98_priority

client = TestClient(app)


def test_detection_amendements_tombants_et_ordre_art98():
    """
    Lorsqu'un article comporte un ou plusieurs amendements de suppression totale,
    les amendements portant sur des alinéas spécifiques de ce même article reçoivent
    `tombe_si_adoption_de: [liste_numeros_suppression]`.
    """
    liasse = [
        {
            "id": "AM-SUP-1",
            "numero": "10",
            "article": "Article 3",
            "dispositif": "Supprimer cet article.",
        },
        {
            "id": "AM-SUP-2",
            "numero": "11",
            "article": "Article 3",
            "dispositif": "<p>Supprimer cet article.</p>",
        },
        {
            "id": "AM-AL-2",
            "numero": "25",
            "article": "Article 3",
            "dispositif": "À l'alinéa 2, substituer au mot : « trois » le mot : « cinq ».",
        },
    ]

    res = classer_par_regles(liasse)
    by_num = {a["numero"]: a for a in res["amendements"]}

    assert by_num["10"]["tombe_si_adoption_de"] == []
    assert by_num["11"]["tombe_si_adoption_de"] == []
    assert by_num["25"]["tombe_si_adoption"] is True
    assert by_num["25"]["tombe_si_adoption_de"] == ["10", "11"]
    assert "⚠️ Tombe si adoption de 10, 11" in by_num["25"]["alerte_tombant"]

    # Vérification de l'ordre d'appel Art. 98 RAN (1 à 5)
    assert compute_art98_priority("Supprimer cet article.")[0] == 1
    assert compute_art98_priority("Rédiger ainsi cet article : « ... »")[0] == 2
    assert compute_art98_priority("Supprimer l'alinéa 4.")[0] == 3
    assert compute_art98_priority("À l'alinéa 2, substituer aux mots « A » les mots « B ».")[0] == 4
    assert compute_art98_priority("Compléter cet article par un alinéa ainsi rédigé :")[0] == 5


def test_rules_engine_art40_art45_and_custom_rules(tmp_path: Path):
    """
    Teste l'ingestion de règles d'irrecevabilité et l'évaluation Art. 40 (charge/recette sans gage)
    et Art. 45 (cavalier législatif hors périmètre du texte initial).
    """
    db_file = tmp_path / "rules_test.db"
    engine = LegislativeRulesEngine(db_path=db_file)
    rag_store = PersistentRAGStore(db_path=db_file)
    rag_store.seed_default_corpus()

    inserted = engine.ingest_rules([
        {
            "rule_id": "IRR-CUSTOM-384",
            "code_article": "Art. 98 RAN",
            "categorie": "Délai de dépôt",
            "titre": "Amendement hors délai de forclusion",
            "description": "Irrecevabilité des amendements déposés après l'expiration du délai de 17 heures.",
            "mots_cles_declencheurs": ["dépôt tardif hors délai"],
            "severite": "BLOQUANTE",
        }
    ])
    assert inserted == 1
    assert engine.count_rules() >= 6

    texte_loi_sport = (
        "Projet de loi relatif à l'organisation des Jeux Olympiques et Paralympiques de 2030, "
        "aux infrastructures sportives de montagne et à la sécurité des compétitions."
    )

    # 1. Amendement cavalier législatif (Art. 45) + création de charge non gagée (Art. 40)
    am_cavalier_et_art40 = {
        "uid": "AM-CAV-40",
        "numero": "401",
        "article": "Article 1er",
        "dispositif": "Il est créé un fonds national d'indemnisation de la pêche hauturière financé par une prise en charge par l'État.",
        "expose_sommaire": "Soutien à la flotte de chalutiers en mer du Nord.",
    }
    eval_res = engine.evaluate_amendment(am_cavalier_et_art40, texte_loi_global=texte_loi_sport, rag_store=rag_store)
    assert eval_res["recevable"] is False
    assert eval_res["alerte_art40"] is True
    assert eval_res["risque_cavalier_art45"] is True
    assert "ALERTE_IRR_ART_40" in eval_res["alertes"]
    assert "RISQUE_CAVALIER_ART_45" in eval_res["alertes"]

    # 2. Amendement dans le périmètre du texte et sans charge nouvelle -> recevable
    am_conforme = {
        "uid": "AM-OK",
        "numero": "402",
        "article": "Article 2",
        "dispositif": "À l'alinéa 1, préciser les normes de sécurité des infrastructures sportives des Jeux Olympiques de 2030.",
        "expose_sommaire": "Sécurité des compétitions sportives de montagne.",
    }
    eval_ok = engine.evaluate_amendment(am_conforme, texte_loi_global=texte_loi_sport, rag_store=rag_store)
    assert eval_ok["recevable"] is True
    assert eval_ok["alerte_art40"] is False
    assert eval_ok["risque_cavalier_art45"] is False


def test_hatvp_influence_graph_ingest_and_check(tmp_path: Path):
    """Teste l'ingestion de déclarations HATVP et la détection de proximité thématique sourcée."""
    db_file = tmp_path / "hatvp_test.db"
    store = HATVPGraphStore(db_path=db_file, auto_seed=False)

    nb = store.ingest_declarations([
        {
            "rep_id": "HATVP-TEST-99",
            "nom_organisation": "Syndicat National de l'Hydroélectricité",
            "secteur": "Énergie & Barrages",
            "thematiques": ["barrages hydroélectriques", "concessions hydrauliques", "énergie renouvelable de montagne"],
            "actions_menees": "Propositions d'amendements sur la prolongation des concessions de barrages hydroélectriques.",
            "cibles_parlementaires": "Commission des affaires économiques",
        }
    ])
    assert nb == 1

    amendement = {
        "uid": "AM-HYDRO-1",
        "dispositif": "Les concessions de barrages hydroélectriques sont prolongées de dix ans pour soutenir l'énergie renouvelable de montagne.",
        "expose_sommaire": "Sécurisation des barrages hydroélectriques.",
        "commission": "Affaires économiques",
    }
    res = store.check_influence(amendement, min_score=0.20)
    assert res["total_matches"] == 1
    assert res["matches"][0]["rep_id"] == "HATVP-TEST-99"
    assert res["matches"][0]["organisation"] == "Syndicat National de l'Hydroélectricité"
    assert res["matches"][0]["score_proximite"] >= 0.25


def test_chrono_debunker_contradiction_and_no_history(tmp_path: Path):
    """
    Teste le Debunker chronologique :
      - Cas `no_history` : retourne strictement `"Information non disponible dans les sources"`.
      - Cas avec contradiction : détecte un amendement de suppression sur un dispositif voté `pour` précédemment.
    """
    db_file = tmp_path / "debunker_test.db"
    store = ChronoDebunkerStore(db_path=db_file)

    am_suppression = {
        "uid": "AM-DEB-1",
        "auteur_ref": "PA720846",
        "auteur_nom": "Bastien Lachaud",
        "groupe_politique": "LFI-NFP",
        "article": "Article 4",
        "dispositif": "Supprimer cet article relatif à la vidéosurveillance algorithmique lors des compétitions sportives.",
        "expose_sommaire": "Opposition à la vidéosurveillance algorithmique.",
    }

    # 1. Base vide -> statut 'no_history' + message strict anti-hallucination
    empty_res = store.check_chronology(am_suppression)
    assert empty_res["status"] == "no_history"
    assert empty_res["message"] == STRICT_NO_SOURCE_MESSAGE
    assert empty_res["answer"] == STRICT_NO_SOURCE_MESSAGE

    # 2. Ingestion d'un scrutin antérieur où le même acteur a voté 'pour' ce même dispositif
    store.ingest_history([
        {
            "entry_id": "SCRUTIN-2023-112",
            "acteur_ref": "PA720846",
            "auteur_nom": "Bastien Lachaud",
            "groupe_acronyme": "LFI-NFP",
            "date_seance": "2023-03-23",
            "type_entree": "scrutin",
            "sujet": "Expérimentation de la vidéosurveillance algorithmique lors des compétitions sportives",
            "position_vote": "pour",
            "resume_position": "Vote favorable en première lecture sur le dispositif de vidéosurveillance.",
        }
    ])

    detected = store.check_chronology(am_suppression)
    assert detected["status"] == "contradiction_detected"
    assert len(detected["contradictions"]) == 1
    assert detected["contradictions"][0]["entry_id"] == "SCRUTIN-2023-112"
    assert detected["contradictions"][0]["contradiction"] is True


def test_batch_job_queue_and_mcp_lot3_tools(tmp_path: Path):
    """Teste la file de jobs `/api/v2/jobs/submit` + `/api/v2/jobs/{job_id}` et les 3 nouveaux outils MCP."""
    liasse = [
        {
            "id": "JOB-AM-1",
            "numero": "1",
            "article": "Article 1er",
            "dispositif": "Supprimer cet article.",
        },
        {
            "id": "JOB-AM-2",
            "numero": "2",
            "article": "Article 1er",
            "dispositif": "À l'alinéa 1, substituer au mot : « deux » le mot : « quatre ».",
        },
    ]

    submit_res = client.post(
        "/api/v2/jobs/submit",
        json={"amendements": liasse, "evaluer_regles": True, "run_async": False},
    )
    assert submit_res.status_code == 200
    job_id = submit_res.json()["job_id"]

    status_res = client.get(f"/api/v2/jobs/{job_id}")
    assert status_res.status_code == 200
    job_data = status_res.json()
    assert job_data["status"] == "completed"
    assert job_data["processed_count"] == 2
    assert job_data["total_count"] == 2
    assert len(job_data["results"]) == 2
    assert "evaluation_regles" in job_data["results"][0]
    assert job_data["results"][1]["tombe_si_adoption_de"] == ["1"]

    # Vérification des 3 nouveaux outils MCP
    registered = set(mcp_server.mcp.tools.keys())
    assert {
        "evaluer_regles_irrecevabilite",
        "verifier_influence_hatvp",
        "debunker_historique_acteur",
    }.issubset(registered)

    mcp_rules = mcp_server.evaluer_regles_irrecevabilite(liasse[0], db_path=str(tmp_path / "mcp_lot3.db"))
    assert mcp_rules["priorite_appel_art98"] == 1

    mcp_hatvp = mcp_server.verifier_influence_hatvp(
        {"uid": "AM-JO", "dispositif": "Sécurité des grands événements et vidéosurveillance algorithmique pour les jeux olympiques."},
        db_path=str(tmp_path / "mcp_lot3.db"),
    )
    assert mcp_hatvp["total_matches"] >= 1

    mcp_debunk = mcp_server.debunker_historique_acteur(liasse[0], db_path=str(tmp_path / "mcp_lot3_empty.db"))
    assert mcp_debunk["status"] == "no_history"
    assert mcp_debunk["answer"] == STRICT_NO_SOURCE_MESSAGE
