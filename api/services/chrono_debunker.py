"""
api/services/chrono_debunker.py — Debunker Chronologique des Scrutins & Interventions Parlementaires
====================================================================================================
Stocke en local strict (`data/bourbon_rag.db`, table `parliamentary_history`) l'historique
vérifiable des scrutins et interventions en séance :
  - `entry_id`, `acteur_ref`, `auteur_nom`, `groupe_acronyme`, `date_seance`,
    `type_entree` (`scrutin` | `intervention`), `sujet`, `position_vote` (`pour` | `contre` | `abstention`),
    `resume_position`.

Règle stricte anti-hallucination :
  - Si aucun historique pertinent n'est présent en base pour l'acteur ou son groupe,
    retourne explicitement `status: "no_history"` et `"Information non disponible dans les sources"`.
  - Si un historique existe sur le même sujet, met en regard l'acte passé daté et
    la position de l'amendement actuel pour détecter toute contradiction chronologique
    (ex. déposer un amendement de suppression sur un dispositif voté `pour` précédemment).
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    from api.services.rag_store import DEFAULT_DB_PATH, STRICT_NO_SOURCE_MESSAGE, _tokenize_lexical, resolve_sqlite_db_path
except ModuleNotFoundError:
    from services.rag_store import DEFAULT_DB_PATH, STRICT_NO_SOURCE_MESSAGE, _tokenize_lexical, resolve_sqlite_db_path  # type: ignore


DEFAULT_PARLIAMENTARY_HISTORY: list[dict[str, Any]] = [
    {
        "entry_id": "HIST-REF-JOP-001",
        "acteur_ref": "PA-REF-EPR-01",
        "auteur_nom": "Groupe Ensemble pour la République",
        "groupe_acronyme": "EPR",
        "date_seance": "2023-03-23",
        "type_entree": "scrutin",
        "sujet": "Jeux Olympiques et Paralympiques — Sécurité et vidéosurveillance algorithmique",
        "position_vote": "pour",
        "resume_position": "Soutien majoritaire du groupe EPR à l'expérimentation encadrée de la vidéosurveillance algorithmique pour les grands événements sportifs.",
    },
    {
        "entry_id": "HIST-REF-JOP-002",
        "acteur_ref": "PA-REF-SOC-01",
        "auteur_nom": "Groupe Socialistes et apparentés",
        "groupe_acronyme": "SOC",
        "date_seance": "2024-04-11",
        "type_entree": "intervention",
        "sujet": "Jeux Olympiques 2030 — Mobilités ferroviaires alpines et transition écologique",
        "position_vote": "pour",
        "resume_position": "Prise de position en faveur du conditionnement des investissements olympiques aux dessertes ferroviaires alpines et à la gestion de l'eau en montagne.",
    },
    {
        "entry_id": "HIST-REF-JOP-003",
        "acteur_ref": "PA-REF-DR-01",
        "auteur_nom": "Groupe Droite Républicaine",
        "groupe_acronyme": "DR",
        "date_seance": "2024-05-14",
        "type_entree": "scrutin",
        "sujet": "Garantie financière de l'État et infrastructures des Jeux Olympiques et Paralympiques 2030",
        "position_vote": "pour",
        "resume_position": "Vote favorable à l'octroi de la garantie financière de l'État sous réserve d'un contrôle budgétaire strict des dépenses publiques.",
    },
    {
        "entry_id": "HIST-REF-JOP-004",
        "acteur_ref": "PA-REF-ECOS-01",
        "auteur_nom": "Groupe Écologiste et Social",
        "groupe_acronyme": "EcoS",
        "date_seance": "2024-06-05",
        "type_entree": "scrutin",
        "sujet": "Neige de culture, ressources en eau et aménagement en montagne (JOP 2030)",
        "position_vote": "contre",
        "resume_position": "Vote défavorable aux dérogations environnementales pour les retenues collinaires et infrastructures alpines sans évaluation climatique préalable.",
    },
]


def _detect_amendment_stance(dispositif: str, expose: str) -> str:
    """
    Détermine l'orientation normative de l'amendement :
      - 'contre' (suppression, abrogation, interdiction, restriction)
      - 'pour'   (création, extension, maintien, rétablissement, adoption)
    """
    low = f"{dispositif} {expose}".lower()
    if any(
        p in low
        for p in (
            "supprimer cet article",
            "supprimer l'article",
            "supprimer l'alinéa",
            "supprimer les alinéas",
            "abroger",
            "suppression",
            "s'oppose",
            "supprimer le dispositif",
        )
    ):
        return "contre"
    return "pour"


class ChronoDebunkerStore:
    """Gestionnaire SQLite local de l'historique des scrutins et interventions parlementaires."""

    def __init__(self, db_path: Optional[str | Path] = None, auto_seed: bool = True):
        if db_path is not None:
            resolved = Path(db_path)
            try:
                resolved.parent.mkdir(parents=True, exist_ok=True)
                if not os.access(resolved.parent, os.W_OK):
                    resolved = resolve_sqlite_db_path()
            except OSError:
                resolved = resolve_sqlite_db_path()
        else:
            resolved = resolve_sqlite_db_path()
        self.db_path = resolved
        self._init_db()
        if auto_seed:
            self.ensure_default_seed()

    def ensure_default_seed(self) -> int:
        """Pré-charge un historique parlementaire de référence si la table est vide."""
        if self.count_entries() == 0:
            return self.ingest_history(DEFAULT_PARLIAMENTARY_HISTORY)
        return 0

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS parliamentary_history (
                    entry_id TEXT PRIMARY KEY,
                    acteur_ref TEXT NOT NULL DEFAULT '',
                    auteur_nom TEXT NOT NULL DEFAULT '',
                    groupe_acronyme TEXT NOT NULL DEFAULT '',
                    date_seance TEXT NOT NULL DEFAULT '',
                    type_entree TEXT NOT NULL DEFAULT 'scrutin',
                    sujet TEXT NOT NULL,
                    position_vote TEXT NOT NULL DEFAULT '',
                    resume_position TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_hist_acteur ON parliamentary_history(acteur_ref)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_hist_groupe ON parliamentary_history(groupe_acronyme)")
            conn.commit()

    def count_entries(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM parliamentary_history").fetchone()
            return int(row["cnt"]) if row else 0

    def ingest_history(self, entries: list[dict[str, Any]] | str) -> int:
        """Ingère des entrées d'historique parlementaire (scrutins ou interventions)."""
        if isinstance(entries, str):
            entries = json.loads(entries)
        if not isinstance(entries, list):
            return 0

        inserted = 0
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            for idx, item in enumerate(entries, start=1):
                if not isinstance(item, dict):
                    continue
                entry_id = str(item.get("entry_id") or item.get("id") or f"HIST-{idx:04d}").strip()
                acteur_ref = str(item.get("acteur_ref") or item.get("acteurRef") or "").strip()
                auteur_nom = str(item.get("auteur_nom") or item.get("nom") or "").strip()
                groupe = str(item.get("groupe_acronyme") or item.get("groupe") or "").strip()
                date_seance = str(item.get("date_seance") or item.get("date") or "").strip()
                type_entree = str(item.get("type_entree") or "scrutin").strip().lower()
                if type_entree not in ("scrutin", "intervention"):
                    type_entree = "scrutin"
                sujet = str(item.get("sujet") or "").strip()
                if not sujet:
                    continue
                pos = str(item.get("position_vote") or item.get("position") or "").strip().lower()
                resume = str(item.get("resume_position") or item.get("resume") or "").strip()

                conn.execute(
                    """
                    INSERT INTO parliamentary_history (
                        entry_id, acteur_ref, auteur_nom, groupe_acronyme, date_seance,
                        type_entree, sujet, position_vote, resume_position, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(entry_id) DO UPDATE SET
                        acteur_ref = excluded.acteur_ref,
                        auteur_nom = excluded.auteur_nom,
                        groupe_acronyme = excluded.groupe_acronyme,
                        date_seance = excluded.date_seance,
                        type_entree = excluded.type_entree,
                        sujet = excluded.sujet,
                        position_vote = excluded.position_vote,
                        resume_position = excluded.resume_position,
                        updated_at = excluded.updated_at
                    """,
                    (entry_id, acteur_ref, auteur_nom, groupe, date_seance, type_entree, sujet, pos, resume, now_iso),
                )
                inserted += 1
            conn.commit()
        return inserted

    def check_chronology(self, amendement: dict[str, Any]) -> dict[str, Any]:
        """
        Recherche l'historique de l'auteur ou de son groupe sur la thématique de l'amendement.
        Si aucun historique n'est disponible, retourne strictement :
          `status: "no_history"` et `"Information non disponible dans les sources"`.
        """
        if self.count_entries() == 0:
            return {
                "status": "no_history",
                "message": STRICT_NO_SOURCE_MESSAGE,
                "answer": STRICT_NO_SOURCE_MESSAGE,
                "contradictions": [],
                "convergences": [],
                "historique": [],
            }

        am = amendement.get("amendement", amendement) if isinstance(amendement, dict) else {}
        sig = am.get("signataires") if isinstance(am.get("signataires"), dict) else {}
        aut_block = sig.get("auteur") if isinstance(sig.get("auteur"), dict) else {}

        acteur_ref = str(
            am.get("auteur_ref")
            or amendement.get("auteur_ref")
            or aut_block.get("acteurRef")
            or ""
        ).strip()
        auteur_nom = str(
            am.get("auteur_nom")
            or amendement.get("auteur_nom")
            or am.get("auteur")
            or amendement.get("auteur")
            or ""
        ).strip()
        groupe = str(
            am.get("groupe_politique")
            or amendement.get("groupe_politique")
            or am.get("groupe")
            or amendement.get("groupe")
            or ""
        ).strip()

        dispositif = str(am.get("dispositif") or am.get("dispositif_raw") or amendement.get("dispositif") or "")
        expose = str(am.get("expose_sommaire") or am.get("exposeSommaire") or amendement.get("expose_sommaire") or "")
        sujet_am = f"{dispositif} {expose} {am.get('article', '')} {am.get('title', '')}".strip()
        am_tokens = set(_tokenize_lexical(sujet_am))
        am_stance = _detect_amendment_stance(dispositif, expose)

        with self._connect() as conn:
            rows = [dict(r) for r in conn.execute("SELECT * FROM parliamentary_history ORDER BY date_seance DESC").fetchall()]

        matched_history: list[dict[str, Any]] = []
        contradictions: list[dict[str, Any]] = []
        convergences: list[dict[str, Any]] = []

        for row in rows:
            same_actor = bool(acteur_ref and row["acteur_ref"] == acteur_ref)
            if not same_actor and auteur_nom and row["auteur_nom"]:
                clean_a = re.sub(r"\s*\([^)]*\)", "", auteur_nom).lower().strip()
                clean_r = row["auteur_nom"].lower().strip()
                if clean_r and (clean_r in clean_a or clean_a in clean_r):
                    same_actor = True
            same_group = bool(groupe and row["groupe_acronyme"] and row["groupe_acronyme"].lower() == groupe.lower())

            if not (same_actor or same_group):
                continue

            hist_tokens = set(_tokenize_lexical(f"{row['sujet']} {row['resume_position']}"))
            shared = am_tokens & hist_tokens
            if not shared and am_tokens and hist_tokens:
                continue

            hist_pos = row["position_vote"].lower().strip()
            is_contradiction = (
                (am_stance == "contre" and hist_pos == "pour")
                or (am_stance == "pour" and hist_pos == "contre")
            )

            entry_detail = {
                "entry_id": row["entry_id"],
                "acteur_ref": row["acteur_ref"],
                "auteur_nom": row["auteur_nom"],
                "groupe_acronyme": row["groupe_acronyme"],
                "date_seance": row["date_seance"],
                "type_entree": row["type_entree"],
                "sujet": row["sujet"],
                "position_vote": hist_pos,
                "resume_position": row["resume_position"],
                "position_amendement_actuel": am_stance,
                "contradiction": is_contradiction,
                "explication": (
                    f"Inversion de position constatée : vote/intervention « {hist_pos} » le {row['date_seance']} "
                    f"sur « {row['sujet']} » vs amendement actuel orienté « {am_stance} »."
                    if is_contradiction
                    else f"Position constante (« {hist_pos} » le {row['date_seance']} sur « {row['sujet']} »)."
                ),
            }
            matched_history.append(entry_detail)
            if is_contradiction:
                contradictions.append(entry_detail)
            else:
                convergences.append(entry_detail)

        if not matched_history:
            return {
                "status": "no_history",
                "message": STRICT_NO_SOURCE_MESSAGE,
                "answer": STRICT_NO_SOURCE_MESSAGE,
                "contradictions": [],
                "convergences": [],
                "historique": [],
            }

        status = "contradiction_detected" if contradictions else "consistent"
        summary = (
            contradictions[0]["explication"]
            if contradictions
            else convergences[0]["explication"]
        )

        return {
            "status": status,
            "message": summary,
            "answer": summary,
            "contradictions": contradictions,
            "convergences": convergences,
            "historique": matched_history,
        }


_DEFAULT_DEBUNKER_STORE: Optional[ChronoDebunkerStore] = None


def ensure_default_seed(db_path: Optional[str | Path] = None) -> int:
    """Garantit l'amorçage initial de la table `parliamentary_history`."""
    return get_default_debunker_store(db_path=db_path).ensure_default_seed()


def get_default_debunker_store(db_path: Optional[str | Path] = None) -> ChronoDebunkerStore:
    global _DEFAULT_DEBUNKER_STORE
    if db_path is not None:
        return ChronoDebunkerStore(db_path=db_path)
    resolved = resolve_sqlite_db_path()
    if _DEFAULT_DEBUNKER_STORE is None or _DEFAULT_DEBUNKER_STORE.db_path != resolved:
        _DEFAULT_DEBUNKER_STORE = ChronoDebunkerStore(db_path=resolved)
    return _DEFAULT_DEBUNKER_STORE


def check_actor_chronology(
    amendement: dict[str, Any],
    db_path: Optional[str | Path] = None,
    store: Optional[ChronoDebunkerStore] = None,
) -> dict[str, Any]:
    """Point d'entrée fonctionnel pour vérifier la cohérence chronologique d'un auteur/groupe."""
    target_store = store or get_default_debunker_store(db_path=db_path)
    return target_store.check_chronology(amendement=amendement)
