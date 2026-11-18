"""
api/services/batch_job_queue.py — File de Jobs Asynchrone pour Calculs Massifs (Serveur GPU)
============================================================================================
Permet de soumettre des liasses massives (jusqu'à `BOURBON_MAX_AMENDEMENTS = 25000`)
en tâche de fond sans bloquer la requête HTTP ni saturer la mémoire :
  - `POST /api/v2/jobs/submit` : crée le job, lance le traitement par lots et retourne `job_id`.
  - `GET /api/v2/jobs/{job_id}` : retourne l'état (`pending`, `running`, `completed`, `failed`,
    `processed_count`, `total_count`, `statistiques`, `results`).
"""

from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

try:
    from api.services.deterministic_classifier import classer_par_regles
    from api.services.rules_engine import get_default_rules_engine
except ModuleNotFoundError:
    from services.deterministic_classifier import classer_par_regles  # type: ignore
    from services.rules_engine import get_default_rules_engine  # type: ignore


class BatchJobManager:
    """Gestionnaire thread-safe de jobs de classification et d'audit par lots."""

    def __init__(self):
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def submit_job(
        self,
        amendements: list[dict[str, Any]],
        texte_loi_global: Optional[str] = None,
        evaluer_regles: bool = True,
        run_async: bool = False,
    ) -> str:
        job_id = f"job-{uuid.uuid4().hex[:12]}"
        total = len(amendements or [])
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "pending",
                "processed_count": 0,
                "total_count": total,
                "created_at": now_iso,
                "updated_at": now_iso,
                "duree_ms": 0,
                "statistiques": {},
                "results": [],
                "error": None,
            }

        if run_async:
            worker = threading.Thread(
                target=self._execute_job,
                args=(job_id, amendements, texte_loi_global, evaluer_regles),
                daemon=True,
            )
            worker.start()
        else:
            self._execute_job(job_id, amendements, texte_loi_global, evaluer_regles)

        return job_id

    def _execute_job(
        self,
        job_id: str,
        amendements: list[dict[str, Any]],
        texte_loi_global: Optional[str],
        evaluer_regles: bool,
    ) -> None:
        t0 = time.perf_counter()
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = "running"
                self._jobs[job_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

        try:
            classified_payload = classer_par_regles(amendements)
            classified_list = classified_payload.get("amendements", [])
            rules_engine = get_default_rules_engine() if evaluer_regles else None

            results: list[dict[str, Any]] = []
            for idx, item in enumerate(classified_list, start=1):
                if rules_engine is not None:
                    eval_res = rules_engine.evaluate_amendment(item, texte_loi_global=texte_loi_global)
                    item["evaluation_regles"] = eval_res
                results.append(item)
                if idx % 50 == 0 or idx == len(classified_list):
                    with self._lock:
                        if job_id in self._jobs:
                            self._jobs[job_id]["processed_count"] = idx
                            self._jobs[job_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

            duree_ms = max(1, int(round((time.perf_counter() - t0) * 1000)))
            with self._lock:
                if job_id in self._jobs:
                    self._jobs[job_id].update({
                        "status": "completed",
                        "processed_count": len(results),
                        "total_count": len(results),
                        "duree_ms": duree_ms,
                        "statistiques": classified_payload.get("statistiques", {}),
                        "results": results,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    })
        except Exception as exc:
            with self._lock:
                if job_id in self._jobs:
                    self._jobs[job_id].update({
                        "status": "failed",
                        "error": str(exc),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    })

    def get_job(self, job_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None


_DEFAULT_JOB_MANAGER: Optional[BatchJobManager] = None


def get_default_job_manager() -> BatchJobManager:
    global _DEFAULT_JOB_MANAGER
    if _DEFAULT_JOB_MANAGER is None:
        _DEFAULT_JOB_MANAGER = BatchJobManager()
    return _DEFAULT_JOB_MANAGER
