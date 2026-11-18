"""
api/services/hatvp_graph.py — Graphe Relationnel d'Influence & Représentants d'Intérêts (HATVP)
===============================================================================================
Stocke en local strict (`data/bourbon_rag.db`, table `hatvp_declarations`) les déclarations
Open Data de la Haute Autorité pour la transparence de la vie publique (HATVP) :
  - `rep_id`, `nom_organisation`, `secteur`, `thematiques_json`, `actions_menees`, `cibles_parlementaires`.

Aucune requête externe n'est effectuée par défaut (100 % Air-Gapped).
Croise les mots-clés/thèmes de l'amendement, la commission saisie et l'exposé sommaire
avec les fiches déclarées pour retourner des indices de proximité sourcés.
"""

from __future__ import annotations

import csv
import io
import json
import math
import os
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    from api.services.rag_store import DEFAULT_DB_PATH, _tokenize_lexical, resolve_sqlite_db_path
except ModuleNotFoundError:
    from services.rag_store import DEFAULT_DB_PATH, _tokenize_lexical, resolve_sqlite_db_path  # type: ignore


DEFAULT_HATVP_DECLARATIONS: list[dict[str, Any]] = [
    {
        "rep_id": "HATVP-REP-001",
        "nom_organisation": "Fédération Française des Télécoms (FFT)",
        "secteur": "Numérique & Télécommunications",
        "thematiques": ["fibre optique", "5G", "infrastructures numériques", "opérateurs télécoms", "réseaux très haut débit"],
        "actions_menees": "Transmission de propositions d'amendements visant à alléger les obligations de déploiement et la fiscalité sur les pylônes et réseaux.",
        "cibles_parlementaires": "Commission des affaires économiques, Commission des finances",
    },
    {
        "rep_id": "HATVP-REP-002",
        "nom_organisation": "France Nature Environnement (FNE)",
        "secteur": "Environnement & Biodiversité",
        "thematiques": ["pesticides", "biodiversité", "transition écologique", "eau", "artificialisation des sols", "énergies renouvelables"],
        "actions_menees": "Publication d'argumentaires législatifs pour interdire les néonicotinoïdes et renforcer les sanctions environnementales.",
        "cibles_parlementaires": "Commission du développement durable et de l'aménagement du territoire",
    },
    {
        "rep_id": "HATVP-REP-003",
        "nom_organisation": "Comité d'Organisation des Jeux Olympiques et Paralympiques (COJOP / Mouvement Sportif)",
        "secteur": "Sport, Événementiel & Collectivités Hôtes",
        "thematiques": [
            "jeux olympiques",
            "jeux paralympiques",
            "sport",
            "mouvement sportif",
            "collectivités hôtes",
            "infrastructures sportives",
            "garantie financière",
            "sites olympiques",
        ],
        "actions_menees": "Auditions parlementaires et notes techniques relatives à l'organisation des Jeux Olympiques et Paralympiques 2030, aux sites olympiques et aux collectivités hôtes.",
        "cibles_parlementaires": "Commission des affaires culturelles et de l'éducation, Commission des lois",
    },
    {
        "rep_id": "HATVP-REP-004",
        "nom_organisation": "Groupement des Mobilités et Infrastructures Ferroviaires Alpines",
        "secteur": "Transports, Mobilités & Infrastructures Alpines",
        "thematiques": [
            "mobilité",
            "infrastructures ferroviaires",
            "transports alpins",
            "desserte ferroviaire",
            "liaison ferroviaire",
            "montagne",
            "accessibilité des stations",
        ],
        "actions_menees": "Propositions d'amendements sur le financement et la planification des infrastructures ferroviaires alpines et des mobilités décarbonées pour les Jeux d'hiver 2030.",
        "cibles_parlementaires": "Commission du développement durable et de l'aménagement du territoire, Commission des finances",
    },
    {
        "rep_id": "HATVP-REP-005",
        "nom_organisation": "Alliance des Technologies de Sécurité et Vidéosurveillance Algorithmique",
        "secteur": "Sécurité, Sûreté & Technologies Numériques",
        "thematiques": [
            "vidéosurveillance algorithmique",
            "vidéoprotection",
            "sécurité des grands événements",
            "drones",
            "sûreté",
            "reconnaissance",
            "forces de l'ordre",
        ],
        "actions_menees": "Contributions techniques en faveur de la prolongation et de l'encadrement des dispositifs de vidéoprotection et de vidéosurveillance algorithmique lors des grands événements sportifs.",
        "cibles_parlementaires": "Commission des lois",
    },
    {
        "rep_id": "HATVP-REP-006",
        "nom_organisation": "Collectif Montagne Eau & Biodiversité Alpine",
        "secteur": "Environnement, Eau & Montagne",
        "thematiques": [
            "gestion de l'eau",
            "neige de culture",
            "biodiversité en montagne",
            "zones humides",
            "enneigement artificiel",
            "étude d'impact environnemental",
            "alpes",
        ],
        "actions_menees": "Sensibilisation des parlementaires sur la préservation des ressources en eau, l'encadrement de la neige de culture et la protection de la biodiversité en montagne.",
        "cibles_parlementaires": "Commission du développement durable et de l'aménagement du territoire",
    },
]


class HATVPGraphStore:
    """Gestionnaire SQLite local des déclarations de représentants d'intérêts HATVP."""

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
        """Pré-charge les déclarations HATVP de référence si la table est vide."""
        if self.count_declarations() == 0:
            return self.ingest_declarations(DEFAULT_HATVP_DECLARATIONS)
        return 0

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS hatvp_declarations (
                    rep_id TEXT PRIMARY KEY,
                    nom_organisation TEXT NOT NULL,
                    secteur TEXT NOT NULL DEFAULT '',
                    thematiques_json TEXT NOT NULL DEFAULT '[]',
                    actions_menees TEXT NOT NULL DEFAULT '',
                    cibles_parlementaires TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def count_declarations(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM hatvp_declarations").fetchone()
            return int(row["cnt"]) if row else 0

    def ingest_declarations(self, payload_data: list[dict[str, Any]] | str) -> int:
        """Ingère un lot JSON ou CSV de déclarations HATVP dans la table locale."""
        entries: list[dict[str, Any]] = []
        if isinstance(payload_data, list):
            entries = [e for e in payload_data if isinstance(e, dict)]
        elif isinstance(payload_data, str):
            text = payload_data.strip()
            if text.startswith("["):
                entries = json.loads(text)
            else:
                reader = csv.DictReader(io.StringIO(text))
                for row in reader:
                    entries.append(dict(row))

        inserted = 0
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            for idx, item in enumerate(entries, start=1):
                rep_id = str(item.get("rep_id") or item.get("id") or f"HATVP-{idx:04d}").strip()
                nom_org = str(item.get("nom_organisation") or item.get("organisation") or "").strip()
                if not nom_org:
                    continue
                secteur = str(item.get("secteur") or "").strip()
                thematiques = item.get("thematiques") or item.get("thematiques_json") or []
                if isinstance(thematiques, str):
                    try:
                        thematiques = json.loads(thematiques)
                    except Exception:
                        thematiques = [t.strip() for t in thematiques.split(";") if t.strip()]
                actions = str(item.get("actions_menees") or item.get("objet_declare") or "").strip()
                cibles = str(item.get("cibles_parlementaires") or "").strip()

                conn.execute(
                    """
                    INSERT INTO hatvp_declarations (
                        rep_id, nom_organisation, secteur, thematiques_json, actions_menees, cibles_parlementaires, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(rep_id) DO UPDATE SET
                        nom_organisation = excluded.nom_organisation,
                        secteur = excluded.secteur,
                        thematiques_json = excluded.thematiques_json,
                        actions_menees = excluded.actions_menees,
                        cibles_parlementaires = excluded.cibles_parlementaires,
                        updated_at = excluded.updated_at
                    """,
                    (rep_id, nom_org, secteur, json.dumps(thematiques, ensure_ascii=False), actions, cibles, now_iso),
                )
                inserted += 1
            conn.commit()
        return inserted

    def check_influence(self, amendement: dict[str, Any], min_score: float = 0.20) -> dict[str, Any]:
        """
        Croise le texte, l'exposé sommaire, la commission et les mots-clés de l'amendement
        avec les déclarations HATVP locales et retourne les correspondances sourcées.
        """
        am = amendement.get("amendement", amendement) if isinstance(amendement, dict) else {}
        uid = str(am.get("uid") or am.get("id") or amendement.get("id") or "AM-INCONNU")
        dispositif = str(am.get("dispositif") or am.get("dispositif_raw") or amendement.get("dispositif") or "")
        expose = str(am.get("expose_sommaire") or am.get("exposeSommaire") or amendement.get("expose_sommaire") or "")
        commission = str(am.get("commission_libelle") or am.get("commission") or amendement.get("commission") or "")
        mots_cles = " ".join(str(x) for x in (am.get("commission_mots_cles") or amendement.get("commission_mots_cles") or []))

        query_text = f"{dispositif} {expose} {commission} {mots_cles}".strip()
        q_tokens = _tokenize_lexical(query_text)
        if not q_tokens:
            return {"amendement_uid": uid, "matches": [], "total_matches": 0}

        q_set = set(q_tokens)
        q_counts = Counter(q_tokens)
        q_norm = math.sqrt(sum(v * v for v in q_counts.values())) or 1.0

        with self._connect() as conn:
            rows = [dict(r) for r in conn.execute("SELECT * FROM hatvp_declarations").fetchall()]

        matches: list[dict[str, Any]] = []
        for row in rows:
            try:
                themes_list = json.loads(row.get("thematiques_json") or "[]")
            except Exception:
                themes_list = []
            themes_str = " ".join(str(t) for t in themes_list)
            doc_text = f"{row['nom_organisation']} {row['secteur']} {themes_str} {row['actions_menees']} {row['cibles_parlementaires']}"
            d_tokens = _tokenize_lexical(doc_text)
            if not d_tokens:
                continue

            d_set = set(d_tokens)
            shared = q_set & d_set
            if not shared:
                continue

            d_counts = Counter(d_tokens)
            d_norm = math.sqrt(sum(v * v for v in d_counts.values())) or 1.0
            cos_sim = sum(q_counts[t] * d_counts[t] for t in shared) / (q_norm * d_norm)

            theme_tokens = set(_tokenize_lexical(themes_str))
            theme_overlap = len(q_set & theme_tokens) / max(1, len(theme_tokens)) if theme_tokens else 0.0

            score = round(min(1.0, 0.55 * cos_sim + 0.45 * theme_overlap + (0.15 if len(shared) >= 3 else 0.0)), 4)
            if score >= min_score:
                matches.append({
                    "rep_id": row["rep_id"],
                    "organisation": row["nom_organisation"],
                    "secteur": row["secteur"],
                    "thematiques": themes_list,
                    "objet_declare": row["actions_menees"],
                    "cibles_parlementaires": row["cibles_parlementaires"],
                    "score_proximite": score,
                })

        matches.sort(key=lambda m: m["score_proximite"], reverse=True)
        return {
            "amendement_uid": uid,
            "total_matches": len(matches),
            "matches": matches,
        }


_DEFAULT_HATVP_STORE: Optional[HATVPGraphStore] = None


def ensure_default_seed(db_path: Optional[str | Path] = None) -> int:
    """Garantit l'amorçage initial de la table `hatvp_declarations`."""
    return get_default_hatvp_store(db_path=db_path).ensure_default_seed()


def get_default_hatvp_store(db_path: Optional[str | Path] = None) -> HATVPGraphStore:
    global _DEFAULT_HATVP_STORE
    if db_path is not None:
        return HATVPGraphStore(db_path=db_path)
    resolved = resolve_sqlite_db_path()
    if _DEFAULT_HATVP_STORE is None or _DEFAULT_HATVP_STORE.db_path != resolved:
        _DEFAULT_HATVP_STORE = HATVPGraphStore(db_path=resolved)
    return _DEFAULT_HATVP_STORE


def check_amendment_influence(
    amendement: dict[str, Any],
    db_path: Optional[str | Path] = None,
    store: Optional[HATVPGraphStore] = None,
    min_score: float = 0.20,
) -> dict[str, Any]:
    """Point d'entrée fonctionnel pour vérifier les proximités d'intérêt HATVP sur un amendement."""
    target_store = store or get_default_hatvp_store(db_path=db_path)
    return target_store.check_influence(amendement=amendement, min_score=min_score)
