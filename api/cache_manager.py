"""
api/cache_manager.py — Cache SQLite pour les verdicts LLM
==========================================================
Évite les inférences redondantes (anti-OOM / anti-surcharge GPU).

Chaque amendement analysé par le moteur sémantique voit son verdict
stocké localement. Avant toute inférence, le pipeline vérifie le cache
et court-circuite l'appel au LLM si le résultat est déjà connu.

La base `bourbon_cache.db` est créée automatiquement au premier accès
dans le répertoire de travail courant (à côté de `api/`).
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from typing import Any, Optional

logger = logging.getLogger("bourbon.cache")

# Chemin absolu vers /tmp pour la compatibilité Vercel Serverless (Read-Only FS)
_DB_PATH = "/tmp/bourbon_cache.db"

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS llm_cache (
    uid                  TEXT PRIMARY KEY,
    statut               TEXT NOT NULL,
    analyse_intention    TEXT,
    analyse_politique    TEXT,
    id_discussion_cible  TEXT,
    niveau_confiance     REAL,
    timestamp            DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

_initialized = False


def _get_connection() -> sqlite3.Connection:
    """Ouvre (ou crée) la base et s'assure que la table existe."""
    global _initialized
    conn = sqlite3.connect(_DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    if not _initialized:
        conn.execute(_CREATE_TABLE_SQL)
        conn.commit()
        _initialized = True
        logger.info(f"📦 Cache SQLite initialisé : {_DB_PATH}")
    return conn


def get_cached_classification(uid: str) -> Optional[dict[str, Any]]:
    """
    Récupère un verdict LLM déjà connu.

    Returns:
        dict avec les clés du schéma LLMClassificationResponse, ou None (MISS).
    """
    try:
        conn = _get_connection()
        row = conn.execute(
            "SELECT statut, analyse_intention, analyse_politique, "
            "id_discussion_cible, niveau_confiance, timestamp "
            "FROM llm_cache WHERE uid = ?",
            (uid,),
        ).fetchone()
        conn.close()

        if row is None:
            return None

        logger.info(f"✅ Cache HIT pour {uid}")
        return {
            "statut": row["statut"],
            "analyse_intention": row["analyse_intention"],
            "analyse_politique": row["analyse_politique"],
            "id_discussion_cible": row["id_discussion_cible"],
            "niveau_confiance": row["niveau_confiance"],
            "cached_at": row["timestamp"],
        }
    except Exception as exc:
        logger.warning(f"⚠️ Erreur lecture cache pour {uid}: {exc}")
        return None


def save_classification(uid: str, data: dict[str, Any]) -> None:
    """
    Persiste un verdict LLM dans le cache SQLite.

    Args:
        uid  : identifiant unique de l'amendement.
        data : dict contenant au minimum `statut`.
    """
    try:
        conn = _get_connection()
        conn.execute(
            "INSERT OR REPLACE INTO llm_cache "
            "(uid, statut, analyse_intention, analyse_politique, "
            "id_discussion_cible, niveau_confiance) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                uid,
                data.get("statut", "NOUVEAU"),
                data.get("analyse_intention", ""),
                data.get("analyse_politique", ""),
                data.get("id_discussion_cible"),
                data.get("niveau_confiance", 0.0),
            ),
        )
        conn.commit()
        conn.close()
        logger.info(f"💾 Cache SAVE pour {uid} → {data.get('statut')}")
    except Exception as exc:
        logger.warning(f"⚠️ Erreur écriture cache pour {uid}: {exc}")


def clear_cache() -> int:
    """Vide entièrement le cache. Retourne le nombre d'entrées supprimées."""
    try:
        conn = _get_connection()
        cursor = conn.execute("DELETE FROM llm_cache")
        count = cursor.rowcount
        conn.commit()
        conn.close()
        logger.info(f"🗑️ Cache vidé : {count} entrée(s) supprimée(s).")
        return count
    except Exception as exc:
        logger.warning(f"⚠️ Erreur lors du vidage du cache : {exc}")
        return 0
