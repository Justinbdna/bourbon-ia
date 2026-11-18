"""
api/services/rules_engine.py — Moteur des Règles d'Irrecevabilité & Cavaliers Législatifs (384 Règles)
======================================================================================================
Stocke et évalue un catalogue extensible de règles légistiques, constitutionnelles et du Règlement AN
dans SQLite (`data/bourbon_rag.db`, table `legislative_rules`) :
  - `rule_id`, `code_article`, `categorie`, `titre`, `description`, `mots_cles_declencheurs`, `severite`.

Évaluation déterministe et hybride (`evaluate_amendment_rules(amendement, texte_loi_global, rag_store)`) :
  1. **Article 40 de la Constitution** : création/aggravation d'une charge publique ou baisse de recettes
     sans gage constitutionnel valide.
  2. **Article 45 de la Constitution (Cavalier législatif)** : calcul de proximité lexicale/cosinus
     entre le dispositif/exposé de l'amendement et le périmètre initial du texte (`texte_loi_global` /
     `texte_loi_reference`). Si la proximité est inférieure au seuil (`< 0.12`, hors champ manifeste),
     lève une alerte `RISQUE_CAVALIER_ART_45`.
  3. **Article 98 du Règlement de l'AN (Ordre d'appel en séance)** : attribue un rang de priorité
     d'appel strict (`1: Suppression d'article`, `2: Rédaction globale`, `3: Suppression d'alinéa`,
     `4: Substitution/Modification`, `5: Insertion/Addition`).
"""

from __future__ import annotations

import csv
import io
import json
import math
import os
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    from api.legal_chapeau_parser import (
        auditer_recevabilite_art40,
        detecter_dispositions_non_normatives,
        parse_chapeau,
    )
except ModuleNotFoundError:
    from legal_chapeau_parser import (  # type: ignore
        auditer_recevabilite_art40,
        detecter_dispositions_non_normatives,
        parse_chapeau,
    )

try:
    from api.services.rag_store import DEFAULT_DB_PATH, PersistentRAGStore, _tokenize_lexical
except ModuleNotFoundError:
    from services.rag_store import DEFAULT_DB_PATH, PersistentRAGStore, _tokenize_lexical  # type: ignore


PRIORITE_ART98_LABELS: dict[int, str] = {
    1: "1: Suppression d'article",
    2: "2: Rédaction globale",
    3: "3: Suppression d'alinéa",
    4: "4: Substitution/Modification",
    5: "5: Insertion/Addition",
}


DEFAULT_RULES_CATALOG: list[dict[str, Any]] = [
    {
        "rule_id": "IRR-ART40-001",
        "code_article": "Art. 40 C.",
        "categorie": "Recevabilité financière",
        "titre": "Création ou aggravation d'une charge publique directe",
        "description": "Tout amendement parlementaire créant un fonds, une agence, une allocation ou une prise en charge par l'État est irrecevable au titre de l'article 40 de la Constitution (une charge ne peut jamais être gagée).",
        "mots_cles_declencheurs": ["création d'un fonds", "prise en charge par l'état", "allocation", "subvention", "indemnité nouvelle", "dotation supplémentaire"],
        "severite": "BLOQUANTE",
    },
    {
        "rule_id": "IRR-ART40-002",
        "code_article": "Art. 40 C.",
        "categorie": "Recevabilité financière",
        "titre": "Diminution de ressources publiques sans gage valide",
        "description": "Toute exonération, réduction d'impôt, abattement ou baisse de taux fiscal doit être compensée à due concurrence par un gage financier recevable (Tabac, Alcool, DGF, Sécurité sociale).",
        "mots_cles_declencheurs": ["exonération", "abattement", "taux réduit", "réduction d'impôt", "crédit d'impôt", "suppression de la taxe"],
        "severite": "BLOQUANTE",
    },
    {
        "rule_id": "IRR-ART45-001",
        "code_article": "Art. 45 C.",
        "categorie": "Cavalier législatif",
        "titre": "Absence de lien direct ou indirect avec le texte en discussion",
        "description": "En première lecture, tout amendement doit présenter un lien, même indirect, avec le texte déposé ou transmis (Article 45 alinéa 1er de la Constitution).",
        "mots_cles_declencheurs": [],
        "severite": "HAUTE",
    },
    {
        "rule_id": "IRR-ART98-001",
        "code_article": "Art. 98 RAN",
        "categorie": "Ordre d'appel en séance",
        "titre": "Hiérarchie d'appel des amendements en séance",
        "description": "Les amendements sont appelés dans l'ordre suivant : 1. Suppression d'article ; 2. Rédaction globale ; 3. Suppression d'alinéa ; 4. Substitution/Modification ; 5. Insertion/Addition.",
        "mots_cles_declencheurs": [],
        "severite": "INFO",
    },
    {
        "rule_id": "IRR-DDHC6-001",
        "code_article": "Art. 6 DDHC",
        "categorie": "Portée normative",
        "titre": "Prohibition des neutrons législatifs (dispositions non normatives)",
        "description": "La loi a pour vocation d'édicter des règles normatives. Les déclarations d'intention dépourvues de portée juridique sont contraires à l'article 6 de la DDHC.",
        "mots_cles_declencheurs": ["a pour objectif de", "la nation reconnaît", "se donne pour mission"],
        "severite": "MOYENNE",
    },
]


def compute_text_proximity(amendment_text: str, reference_text: str) -> float:
    """
    Calcule la proximité lexicale / cosinus entre le texte d'un amendement et le
    périmètre du texte de loi initial (`texte_loi_global`), calibrée sur [0.0, 1.0].
    """
    toks_a = _tokenize_lexical(amendment_text)
    toks_b = _tokenize_lexical(reference_text)
    if not toks_a or not toks_b:
        return 0.0

    set_a = set(toks_a)
    set_b = set(toks_b)
    shared = set_a & set_b
    if not shared:
        return 0.0

    cnt_a = Counter(toks_a)
    cnt_b = Counter(toks_b)
    dot = sum(cnt_a[t] * cnt_b[t] for t in shared)
    norm_a = math.sqrt(sum(v * v for v in cnt_a.values())) or 1.0
    norm_b = math.sqrt(sum(v * v for v in cnt_b.values())) or 1.0
    cos_sim = dot / (norm_a * norm_b)

    coverage_a = len(shared) / max(1, len(set_a))
    score = 0.55 * cos_sim + 0.45 * coverage_a
    return round(max(0.0, min(1.0, score)), 4)


def compute_art98_priority(dispositif: str) -> tuple[int, str]:
    """
    Attribue un rang de priorité d'appel strict selon l'Article 98 du Règlement de l'AN :
      1: Suppression d'article
      2: Rédaction globale
      3: Suppression d'alinéa
      4: Substitution/Modification
      5: Insertion/Addition
    """
    clean = (dispositif or "").strip()
    low = clean.lower()
    chapeau = parse_chapeau(clean)

    if (
        "supprimer cet article" in low
        or "supprimer l'article" in low
        or "supprimer l\u2019article" in low
        or (chapeau.verbe_action == "SUPPRIMER" and chapeau.cible_type == "Article entier")
    ):
        return 1, PRIORITE_ART98_LABELS[1]

    if (
        "rédiger ainsi cet article" in low
        or "rediger ainsi cet article" in low
        or "rédiger ainsi l'article" in low
        or (chapeau.verbe_action == "REDIGER_AINSI" and chapeau.cible_type == "Article entier")
    ):
        return 2, PRIORITE_ART98_LABELS[2]

    if (
        re.search(r"\bsupprimer\s+l['\u2019\s]*alin[eé]a\b", low)
        or re.search(r"\bsupprimer\s+les\s+alin[eé]as\b", low)
        or (chapeau.verbe_action == "SUPPRIMER" and chapeau.cible_type in ("Alinéa", "ALINEA"))
    ):
        return 3, PRIORITE_ART98_LABELS[3]

    if (
        chapeau.verbe_action in ("SUBSTITUER", "REMPLACER", "REDIGER_AINSI", "SUPPRIMER")
        or any(w in low for w in ("substituer", "remplacer", "rédiger ainsi l'alinéa", "supprimer le mot", "supprimer les mots"))
    ):
        return 4, PRIORITE_ART98_LABELS[4]

    return 5, PRIORITE_ART98_LABELS[5]


class LegislativeRulesEngine:
    """Gestionnaire SQLite et moteur d'évaluation des 384 règles d'irrecevabilité."""

    def __init__(self, db_path: Optional[str | Path] = None, auto_seed: bool = True):
        resolved = Path(db_path or os.getenv("BOURBON_RAG_DB_PATH") or DEFAULT_DB_PATH)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = resolved
        self._init_db()
        if auto_seed and self.count_rules() == 0:
            self.ingest_rules(DEFAULT_RULES_CATALOG)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS legislative_rules (
                    rule_id TEXT PRIMARY KEY,
                    code_article TEXT NOT NULL DEFAULT '',
                    categorie TEXT NOT NULL DEFAULT '',
                    titre TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    mots_cles_declencheurs TEXT NOT NULL DEFAULT '[]',
                    severite TEXT NOT NULL DEFAULT 'HAUTE',
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rules_code ON legislative_rules(code_article)")
            conn.commit()

    def count_rules(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM legislative_rules").fetchone()
            return int(row["cnt"]) if row else 0

    def list_rules(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM legislative_rules ORDER BY rule_id").fetchall()
            out = []
            for r in rows:
                d = dict(r)
                try:
                    d["mots_cles_declencheurs"] = json.loads(d.get("mots_cles_declencheurs") or "[]")
                except Exception:
                    d["mots_cles_declencheurs"] = []
                out.append(d)
            return out

    def ingest_rules(self, payload_data: list[dict[str, Any]] | str) -> int:
        """
        Importe en masse des règles légistiques (accepte une liste JSON, du CSV ou du Markdown).
        """
        rules_list: list[dict[str, Any]] = []
        if isinstance(payload_data, list):
            rules_list = [r for r in payload_data if isinstance(r, dict)]
        elif isinstance(payload_data, str):
            text = payload_data.strip()
            if text.startswith("["):
                rules_list = json.loads(text)
            elif "," in text.splitlines()[0] and "rule_id" in text.splitlines()[0]:
                reader = csv.DictReader(io.StringIO(text))
                for row in reader:
                    kws = [k.strip() for k in (row.get("mots_cles_declencheurs") or "").split(";") if k.strip()]
                    rules_list.append({
                        "rule_id": row.get("rule_id") or "",
                        "code_article": row.get("code_article") or "",
                        "categorie": row.get("categorie") or "",
                        "titre": row.get("titre") or "",
                        "description": row.get("description") or "",
                        "mots_cles_declencheurs": kws,
                        "severite": row.get("severite") or "HAUTE",
                    })
            else:
                for idx, line in enumerate(text.splitlines(), start=1):
                    clean_line = line.strip().lstrip("-* ").strip()
                    if len(clean_line) >= 10:
                        rules_list.append({
                            "rule_id": f"RULE-MD-{idx:03d}",
                            "code_article": "Règle Légistique",
                            "categorie": "Recevabilité",
                            "titre": clean_line[:80],
                            "description": clean_line,
                            "mots_cles_declencheurs": [],
                            "severite": "MOYENNE",
                        })

        inserted = 0
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            for idx, r in enumerate(rules_list, start=1):
                rule_id = str(r.get("rule_id") or r.get("id") or f"RULE-{idx:03d}").strip()
                code_article = str(r.get("code_article") or r.get("article") or "RAN").strip()
                categorie = str(r.get("categorie") or "Recevabilité").strip()
                titre = str(r.get("titre") or r.get("title") or rule_id).strip()
                description = str(r.get("description") or r.get("texte") or "").strip()
                kws = r.get("mots_cles_declencheurs") or []
                if isinstance(kws, str):
                    kws = [k.strip() for k in kws.split(",") if k.strip()]
                severite = str(r.get("severite") or "HAUTE").strip().upper()

                conn.execute(
                    """
                    INSERT INTO legislative_rules (
                        rule_id, code_article, categorie, titre, description, mots_cles_declencheurs, severite, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(rule_id) DO UPDATE SET
                        code_article = excluded.code_article,
                        categorie = excluded.categorie,
                        titre = excluded.titre,
                        description = excluded.description,
                        mots_cles_declencheurs = excluded.mots_cles_declencheurs,
                        severite = excluded.severite,
                        updated_at = excluded.updated_at
                    """,
                    (rule_id, code_article, categorie, titre, description, json.dumps(kws, ensure_ascii=False), severite, now_iso),
                )
                inserted += 1
            conn.commit()
        return inserted

    def evaluate_amendment(
        self,
        amendement: dict[str, Any],
        texte_loi_global: Optional[str] = None,
        rag_store: Optional[PersistentRAGStore] = None,
        cavalier_threshold: float = 0.12,
    ) -> dict[str, Any]:
        """
        Évalue un amendement contre l'Article 40 C., l'Article 45 C. (Cavalier législatif),
        l'Article 98 RAN (Ordre d'appel) et le catalogue des règles actives en base.
        """
        am = amendement.get("amendement", amendement) if isinstance(amendement, dict) else {}
        uid = str(am.get("uid") or am.get("id") or amendement.get("id") or "AM-INCONNU")
        numero = str(am.get("numero") or amendement.get("numero") or uid)
        dispositif = str(am.get("dispositif") or am.get("dispositif_raw") or amendement.get("dispositif") or "")
        expose = str(am.get("expose_sommaire") or am.get("exposeSommaire") or amendement.get("expose_sommaire") or "")
        texte_complet_am = f"{dispositif}\n{expose}".strip()
        low_am = texte_complet_am.lower()

        violations: list[dict[str, Any]] = []

        # 1. Évaluation Article 40 C. (Recevabilité financière)
        audit_40 = auditer_recevabilite_art40(dispositif, amendement)
        alerte_art40 = bool(audit_40["alerte_recevabilite_art40"])
        if alerte_art40:
            violations.append({
                "rule_id": "IRR-ART40",
                "code": "ALERTE_IRR_ART_40",
                "code_article": "Art. 40 C.",
                "severite": "BLOQUANTE",
                "motif": audit_40["motif_art40"] or "Risque d'irrecevabilité financière au titre de l'article 40 de la Constitution.",
            })

        # 2. Évaluation Article 45 C. (Cavalier législatif — Proximité avec le périmètre du texte)
        ref_text = (
            texte_loi_global
            or am.get("texte_loi_reference")
            or amendement.get("texte_loi_reference")
            or am.get("dossier_titre")
            or amendement.get("title")
            or ""
        )
        proximite_score = compute_text_proximity(texte_complet_am, str(ref_text)) if ref_text else 1.0
        risque_cavalier = False
        if ref_text and texte_complet_am and proximite_score < cavalier_threshold:
            risque_cavalier = True
            violations.append({
                "rule_id": "IRR-ART45-001",
                "code": "RISQUE_CAVALIER_ART_45",
                "code_article": "Art. 45 C.",
                "severite": "HAUTE",
                "motif": (
                    f"Proximité sémantique/lexicale très faible ({proximite_score:.2f} < {cavalier_threshold}) "
                    f"avec le périmètre initial du texte : risque de cavalier législatif (Article 45 C.)."
                ),
            })

        # 3. Évaluation Article 98 RAN (Ordre d'appel en séance)
        rang_art98, libelle_art98 = compute_art98_priority(dispositif)

        # 4. Détection non-normatif (Art. 6 DDHC)
        non_norm = detecter_dispositions_non_normatives(dispositif)
        if non_norm.get("alerte_non_normatif"):
            violations.append({
                "rule_id": "IRR-DDHC6-001",
                "code": "ALERTE_NON_NORMATIF",
                "code_article": "Art. 6 DDHC",
                "severite": "MOYENNE",
                "motif": non_norm.get("motif_non_normatif"),
            })

        # 5. Vérification des règles personnalisées du catalogue (384 règles)
        existing_ids = {v["rule_id"] for v in violations}
        for rule in self.list_rules():
            r_id = rule["rule_id"]
            if r_id in existing_ids or r_id in ("IRR-ART40-001", "IRR-ART40-002", "IRR-ART45-001", "IRR-ART98-001", "IRR-DDHC6-001"):
                continue
            triggers = rule.get("mots_cles_declencheurs") or []
            matched_triggers = [kw for kw in triggers if kw and kw.lower() in low_am]
            if matched_triggers:
                violations.append({
                    "rule_id": r_id,
                    "code": f"ALERTE_{r_id}",
                    "code_article": rule["code_article"],
                    "severite": rule["severite"],
                    "motif": f"{rule['titre']} — {rule['description']} (déclencheur : {', '.join(matched_triggers)})",
                })

        # 6. Sourçage RAG complémentaire si un rag_store est fourni
        sources_rag = []
        if rag_store is not None and texte_complet_am:
            rag_res = rag_store.query_rag(texte_complet_am, top_k=2, min_score=0.45, source_type="regle_irrecevabilite")
            sources_rag = rag_res.get("results", [])

        return {
            "amendement_uid": uid,
            "numero": numero,
            "recevable": not any(v["severite"] == "BLOQUANTE" for v in violations) and not risque_cavalier,
            "alerte_art40": alerte_art40,
            "gage_detecte": audit_40["gage_detecte"],
            " motif_art40": audit_40["motif_art40"],
            "motif_art40": audit_40["motif_art40"],
            "risque_cavalier_art45": risque_cavalier,
            "proximite_texte_score": proximite_score,
            "priorite_appel_art98": rang_art98,
            "libelle_appel_art98": libelle_art98,
            "alertes": [v["code"] for v in violations],
            "violations": violations,
            "sources_rag": sources_rag,
        }


_DEFAULT_RULES_ENGINE: Optional[LegislativeRulesEngine] = None


def get_default_rules_engine(db_path: Optional[str | Path] = None) -> LegislativeRulesEngine:
    global _DEFAULT_RULES_ENGINE
    if db_path is not None:
        return LegislativeRulesEngine(db_path=db_path)
    if _DEFAULT_RULES_ENGINE is None:
        _DEFAULT_RULES_ENGINE = LegislativeRulesEngine()
    return _DEFAULT_RULES_ENGINE


def evaluate_amendment_rules(
    amendement: dict[str, Any],
    texte_loi_global: Optional[str] = None,
    rag_store: Optional[PersistentRAGStore] = None,
    db_path: Optional[str | Path] = None,
    engine: Optional[LegislativeRulesEngine] = None,
) -> dict[str, Any]:
    """Point d'entrée fonctionnel pour évaluer un amendement contre le catalogue des règles."""
    target_engine = engine or get_default_rules_engine(db_path=db_path)
    return target_engine.evaluate_amendment(
        amendement=amendement,
        texte_loi_global=texte_loi_global,
        rag_store=rag_store,
    )
