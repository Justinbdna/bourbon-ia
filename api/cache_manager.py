"""
api/cache_manager.py — Cache en mémoire RAM avec TTL (Option 2) pour Bourbon.IA
================================================================================
Remplace l'ancien cache SQLite (/tmp/bourbon_cache.db) pour éliminer définitivement
les verrous "database is locked" en environnement serverless (Vercel) et accélérer
les lectures/écritures de verdicts LLM.

Spécifications techniques :
  - Thread-safe via threading.RLock()
  - Stockage en mémoire RAM : {cle: (donnees_dict, timestamp_expiration)}
  - TTL par défaut : 3 600 secondes (1 heure)
  - Capacité maximale : 2 000 entrées avec éviction FIFO/LRU des plus anciennes
  - Purge automatique des entrées expirées
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from typing import Any, Optional

logger = logging.getLogger("bourbon.cache")

DEFAULT_TTL_SECONDS = 3600
MAX_CACHE_ENTRIES = 2000


class InMemoryCache:
    """Cache en mémoire thread-safe avec TTL et limitation de capacité."""

    def __init__(self, max_entries: int = MAX_CACHE_ENTRIES, default_ttl: int = DEFAULT_TTL_SECONDS):
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        # OrderedDict pour maintenir l'ordre d'insertion/accès et faciliter l'éviction
        self._cache: OrderedDict[str, tuple[dict[str, Any], float]] = OrderedDict()
        self._lock = threading.RLock()

    def _purge_expired(self, now: Optional[float] = None) -> None:
        """Nettoie les entrées dont la date d'expiration est dépassée."""
        if now is None:
            now = time.time()
        expired_keys = [k for k, (_, expire_at) in self._cache.items() if now >= expire_at]
        for k in expired_keys:
            del self._cache[k]

    def get(self, key: str) -> Optional[dict[str, Any]]:
        """
        Récupère une entrée du cache si elle existe et n'est pas expirée.

        Returns:
            dict avec les clés du résultat LLM, ou None (MISS / expirée).
        """
        with self._lock:
            if key not in self._cache:
                return None

            data, expire_at = self._cache[key]
            now = time.time()
            if now >= expire_at:
                del self._cache[key]
                logger.debug(f"⏰ Cache EXPIRED pour {key}")
                return None

            # Déplacer en fin pour comportement LRU
            self._cache.move_to_end(key)
            logger.info(f"✅ Cache HIT pour {key}")
            cached_data = dict(data)
            cached_data["cached"] = True
            return cached_data

    def set(self, key: str, value: dict[str, Any], ttl: Optional[int] = None) -> None:
        """
        Stocke ou met à jour une entrée avec son timestamp d'expiration.
        Purge les expirées et applique une éviction si la capacité maximale est atteinte.
        """
        ttl_seconds = ttl if ttl is not None else self.default_ttl
        now = time.time()
        expire_at = now + ttl_seconds

        with self._lock:
            # 1. Purge des clés expirées
            self._purge_expired(now)

            # 2. Si la clé existe déjà, mise à jour
            if key in self._cache:
                self._cache[key] = (dict(value), expire_at)
                self._cache.move_to_end(key)
                return

            # 3. Éviction si capacité dépassée
            if len(self._cache) >= self.max_entries:
                oldest_key, _ = self._cache.popitem(last=False)
                logger.debug(f"♻️ Éviction cache (capacité max) : {oldest_key}")

            # 4. Insertion
            self._cache[key] = (dict(value), expire_at)
            logger.info(f"💾 Cache SAVE pour {key} (TTL: {ttl_seconds}s)")

    def clear(self) -> int:
        """Vide l'intégralité du cache. Retourne le nombre d'éléments supprimés."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"🗑️ Cache mémoire vidé : {count} entrée(s).")
            return count

    def size(self) -> int:
        """Nombre d'entrées actives en cache (après purge des expirées)."""
        with self._lock:
            self._purge_expired()
            return len(self._cache)


# ── Instance Singleton Globale ──
_MEMORY_CACHE = InMemoryCache()


def _build_cache_key(
    uid: str,
    context_key: Optional[str] = None,
    model: Optional[str] = None,
    candidats: Optional[list[dict[str, Any]]] = None,
) -> str:
    if model is not None or candidats is not None:
        cand_ids = sorted(
            str(c.get("id_discussion") or c.get("uid") or "")
            for c in (candidats or [])
            if isinstance(c, dict)
        )
        raw_sig = f"{model or ''}|{'|'.join(cand_ids)}|{context_key or ''}"
        digest = hashlib.sha256(raw_sig.encode("utf-8")).hexdigest()[:16]
        return f"{uid}::{digest}"
    if context_key:
        digest = hashlib.sha256(str(context_key).encode("utf-8")).hexdigest()[:16]
        return f"{uid}::{digest}"
    return uid


def get_cached_classification(
    uid: str,
    context_key: Optional[str] = None,
    model: Optional[str] = None,
    candidats: Optional[list[dict[str, Any]]] = None,
) -> Optional[dict[str, Any]]:
    """Accès au cache en mémoire compatible avec l'API FastAPI Bourbon.IA."""
    return _MEMORY_CACHE.get(_build_cache_key(uid, context_key=context_key, model=model, candidats=candidats))


def save_classification(
    uid: str,
    data: dict[str, Any],
    ttl: int = DEFAULT_TTL_SECONDS,
    context_key: Optional[str] = None,
    model: Optional[str] = None,
    candidats: Optional[list[dict[str, Any]]] = None,
) -> None:
    """Sauvegarde dans le cache en mémoire compatible avec l'API FastAPI Bourbon.IA."""
    _MEMORY_CACHE.set(_build_cache_key(uid, context_key=context_key, model=model, candidats=candidats), data, ttl=ttl)


def clear_cache() -> int:
    """Vidage complet du cache en mémoire."""
    return _MEMORY_CACHE.clear()
