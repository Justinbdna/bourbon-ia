"""
mcp_server.py — Serveur Model Context Protocol (MCP) 100 % Local & Souverain pour Bourbon.IA
=============================================================================================
Permet à tout client MCP local (Antigravity, Claude Desktop, IDE) de piloter Bourbon.IA
sans passer par le navigateur ni exposer de données vers des services Cloud externes.

Outils exposés :
  1. `classer_liasse_mecanique(amendements_json)` : exécute le moteur déterministe V2
     et retourne les statistiques + groupes `[Id.]` / `[Dc.]`.
  2. `inspecter_amendement(uid, amendements_json)` : retourne la fiche légistique complète,
     les alertes Art. 40 / Art. 45 / Art. 98 et les concurrents de division.
  3. `rechercher_sources_rag(requete, top_k=5, min_score=0.45)` : interroge le Vector Store
     SQLite persistant (`data/bourbon_rag.db`) avec citations exactes ou retourne
     strictement `"Information non disponible dans les sources"`.
  4. `generer_prejaune_rtf(amendements_json)` : génère le document RTF "préjaune" officiel
     avec crochets (`╓ ║ ╙`) et étiquettes `[Id.]` / `[Dc.]` prêt pour la séance.
"""

from __future__ import annotations

import inspect
import json
import sys
from datetime import datetime
from typing import Any, Callable, Optional

from api.deterministic_engine import process_deterministic_sorting, qualify_irrecevabilite
from api.index import _build_enriched, _inject_textes_reference, _to_frontend
from api.services.chrono_debunker import ChronoDebunkerStore, check_actor_chronology, get_default_debunker_store
from api.services.hatvp_graph import HATVPGraphStore, check_amendment_influence, get_default_hatvp_store
from api.services.rag_store import STRICT_NO_SOURCE_MESSAGE, PersistentRAGStore, get_default_rag_store, query_rag
from api.services.rules_engine import LegislativeRulesEngine, evaluate_amendment_rules, get_default_rules_engine
from api.textes_resolver import extract_texte_ref, get_textes_reference


# ──────────────────────────────────────────────────────────────────────────
# Adaptateur MCP officiel (`mcp.server.fastmcp.FastMCP`) avec repli JSON-RPC
# natif si le paquet `mcp` n'est pas installé dans l'environnement courant.
# ──────────────────────────────────────────────────────────────────────────
class _LocalFastMCP:
    """Implémentation légère compatible FastMCP (JSON-RPC 2.0 sur stdio + registre d'outils)."""

    def __init__(self, name: str):
        self.name = name
        self.tools: dict[str, dict[str, Any]] = {}

    def tool(self, name: Optional[str] = None, description: Optional[str] = None) -> Callable:
        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            tool_desc = (description or inspect.getdoc(func) or "").strip()
            sig = inspect.signature(func)
            properties: dict[str, Any] = {}
            required: list[str] = []
            for param_name, param in sig.parameters.items():
                properties[param_name] = {"type": "string", "description": f"Paramètre {param_name}"}
                if param.default is inspect.Parameter.empty:
                    required.append(param_name)

            self.tools[tool_name] = {
                "name": tool_name,
                "description": tool_desc,
                "function": func,
                "inputSchema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            }
            return func

        return decorator

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": meta["name"],
                "description": meta["description"],
                "inputSchema": meta["inputSchema"],
            }
            for meta in self.tools.values()
        ]

    def call_tool(self, name: str, arguments: Optional[dict[str, Any]] = None) -> Any:
        if name not in self.tools:
            raise ValueError(f"Outil MCP inconnu : {name}")
        func = self.tools[name]["function"]
        return func(**(arguments or {}))

    def run(self) -> None:
        """Boucle JSON-RPC 2.0 minimale sur stdin/stdout conforme au protocole MCP."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                req_id = req.get("id")
                method = req.get("method", "")
                params = req.get("params") or {}

                if method == "initialize":
                    result = {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": self.name, "version": "1.0.0"},
                        "capabilities": {"tools": {}},
                    }
                elif method == "tools/list":
                    result = {"tools": self.list_tools()}
                elif method == "tools/call":
                    tool_name = params.get("name", "")
                    tool_args = params.get("arguments") or {}
                    output = self.call_tool(tool_name, tool_args)
                    text_out = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
                    result = {"content": [{"type": "text", "text": text_out}]}
                else:
                    result = {}

                if req_id is not None:
                    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result}, ensure_ascii=False) + "\n")
                    sys.stdout.flush()
            except Exception as exc:
                sys.stdout.write(
                    json.dumps(
                        {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(exc)}},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                sys.stdout.flush()


try:
    from mcp.server.fastmcp import FastMCP as _OfficialFastMCP  # type: ignore

    class BourbonMCPServer(_OfficialFastMCP):  # type: ignore
        def __init__(self, name: str):
            super().__init__(name)
            self.tools: dict[str, dict[str, Any]] = {}

        def tool(self, name: Optional[str] = None, description: Optional[str] = None) -> Callable:
            parent_decorator = super().tool(name=name, description=description)

            def decorator(func: Callable) -> Callable:
                t_name = name or func.__name__
                t_desc = (description or inspect.getdoc(func) or "").strip()
                self.tools[t_name] = {"name": t_name, "description": t_desc, "function": func}
                return parent_decorator(func)

            return decorator

        def list_tools_sync(self) -> list[dict[str, Any]]:
            return [{"name": k, "description": v["description"]} for k, v in self.tools.items()]

except ImportError:
    BourbonMCPServer = _LocalFastMCP  # type: ignore


mcp = BourbonMCPServer("Bourbon.IA")


def _parse_amendements_input(amendements_json: str | list[dict[str, Any]] | dict[str, Any]) -> list[dict[str, Any]]:
    """Parse une entrée JSON (str, list ou dict contenant la clé 'amendements')."""
    if isinstance(amendements_json, str):
        parsed = json.loads(amendements_json)
    else:
        parsed = amendements_json

    if isinstance(parsed, dict):
        if "amendements" in parsed and isinstance(parsed["amendements"], list):
            return parsed["amendements"]
        return [parsed]
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    return []


def _executer_pipeline_mecanique(raw_list: list[dict[str, Any]]) -> tuple[list[Any], list[dict[str, Any]]]:
    """Construit les EnrichedAmendment, injecte les textes de référence locaux et exécute le tri déterministe."""
    enriched = []
    for i, raw in enumerate(raw_list):
        enriched.append(_build_enriched(raw, i))

    if not enriched:
        return [], []

    texte_ref_id = extract_texte_ref(raw_list)
    if texte_ref_id:
        textes_ref = get_textes_reference(texte_ref_id)
        if textes_ref:
            _inject_textes_reference(enriched, textes_ref)

    sorted_enriched = process_deterministic_sorting(enriched)
    frontend_items = []
    for rang, a in enumerate(sorted_enriched, start=1):
        mapped = _to_frontend(a)
        mapped["rang"] = rang
        if mapped.get("resultat_ia"):
            mapped["resultat_ia"]["rang"] = rang
        frontend_items.append(mapped)

    return sorted_enriched, frontend_items


# ══════════════════════════════════════════════════════════════════════════
# OUTIL MCP 1 : classer_liasse_mecanique
# ══════════════════════════════════════════════════════════════════════════
@mcp.tool()
def classer_liasse_mecanique(amendements_json: str | list[dict[str, Any]] | dict[str, Any]) -> dict[str, Any]:
    """
    Exécute le moteur déterministe V2 de Bourbon.IA sur une liasse d'amendements
    et retourne les statistiques ainsi que les groupes d'identiques [Id.] et de
    discussion commune [Dc.].
    """
    raw_list = _parse_amendements_input(amendements_json)
    if not raw_list:
        return {
            "total": 0,
            "statistiques": {},
            "groupes_identiques": {},
            "groupes_discussion_commune": {},
            "amendements": [],
        }

    _, items = _executer_pipeline_mecanique(raw_list)
    by_uid = {str(it.get("id")): it for it in items}

    stats: dict[str, int] = {}
    groupes_id: dict[str, list[str]] = {}
    groupes_dc: dict[str, list[str]] = {}

    for item in items:
        statut = (item.get("resultat_ia") or {}).get("statut") or str(item.get("statut_mecanique") or "Inconnu")
        stats[statut] = stats.get(statut, 0) + 1

        grp = (item.get("resultat_ia") or {}).get("groupe")
        num_label = str(item.get("numero") or item.get("id"))
        gid = (grp.get("groupe_id") if isinstance(grp, dict) else None) or item.get("groupe_identique_id")
        if gid:
            gid_str = str(gid)
            if isinstance(grp, dict) and grp.get("type") == "discussion_commune":
                if num_label not in groupes_dc.setdefault(gid_str, []):
                    groupes_dc[gid_str].append(num_label)
            else:
                # Inclure l'amendement référent du groupe d'identiques s'il est mentionné dans la justification
                justif = str(item.get("justification_mecanique") or "")
                for uid_cand, cand_item in by_uid.items():
                    if uid_cand in justif:
                        ref_num = str(cand_item.get("numero") or uid_cand)
                        if ref_num not in groupes_id.setdefault(gid_str, []):
                            groupes_id[gid_str].append(ref_num)
                if num_label not in groupes_id.setdefault(gid_str, []):
                    groupes_id[gid_str].append(num_label)

    return {
        "total": len(items),
        "statistiques": stats,
        "groupes_identiques": groupes_id,
        "groupes_discussion_commune": groupes_dc,
        "amendements": items,
    }


# ══════════════════════════════════════════════════════════════════════════
# OUTIL MCP 2 : inspecter_amendement
# ══════════════════════════════════════════════════════════════════════════
@mcp.tool()
def inspecter_amendement(
    uid: str,
    amendements_json: str | list[dict[str, Any]] | dict[str, Any],
) -> dict[str, Any]:
    """
    Retourne la fiche légistique complète d'un amendement (identifié par son UID ou numéro),
    ses alertes de recevabilité (Art. 40, Art. 45, Art. 98, amendement tombant)
    et la liste des amendements concurrents sur la même division.
    """
    raw_list = _parse_amendements_input(amendements_json)
    sorted_enriched, items = _executer_pipeline_mecanique(raw_list)

    target_uid = str(uid or "").strip()
    target_item = None
    target_enriched = None

    for enr, item in zip(sorted_enriched, items):
        if target_uid in (str(item.get("id")), str(item.get("uid")), str(item.get("numero"))):
            target_item = item
            target_enriched = enr
            break

    if not target_item or not target_enriched:
        return {
            "status": "not_found",
            "message": STRICT_NO_SOURCE_MESSAGE,
            "uid": target_uid,
        }

    irrecevabilite = qualify_irrecevabilite(target_enriched)
    concurrents = [
        {
            "uid": other.get("id"),
            "numero": other.get("numero"),
            "auteur": other.get("auteur_string"),
            "groupe": other.get("groupe_politique"),
            "statut": (other.get("resultat_ia") or {}).get("statut"),
            "priorite_appel": other.get("priorite_appel"),
        }
        for other in items
        if other.get("id") != target_item.get("id") and other.get("article") == target_item.get("article")
    ]

    return {
        "status": "ok",
        "fiche_legistique": {
            "uid": target_item.get("id"),
            "numero": target_item.get("numero"),
            "article": target_item.get("article"),
            "rang": target_item.get("rang"),
            "auteur": target_item.get("auteur_string"),
            "groupe_politique": target_item.get("groupe_politique"),
            "role": target_item.get("role"),
            "dispositif": target_item.get("dispositif"),
            "expose_sommaire": target_item.get("expose_sommaire"),
            "texte_loi_reference": target_item.get("texte_loi_reference"),
            "statut_mecanique": target_item.get("statut_mecanique"),
            "resultat_ia": target_item.get("resultat_ia"),
        },
        "alertes_recevabilite": {
            "est_gage_art40": bool(target_item.get("est_gage")),
            "est_cavalier_art45": bool(target_item.get("est_cavalier_art45")),
            "alerte_art45": target_item.get("alerte_art45"),
            "irrecevabilite_qualifiee": irrecevabilite,
            "priorite_appel_art98": target_item.get("priorite_appel"),
            "libelle_appel_art98": target_item.get("libelle_appel"),
            "tombe_si_adoption": bool(target_item.get("tombe_si_adoption")),
            "alerte_tombant": target_item.get("alerte_tombant"),
        },
        "concurrents_division": concurrents,
    }


# ══════════════════════════════════════════════════════════════════════════
# OUTIL MCP 3 : rechercher_sources_rag
# ══════════════════════════════════════════════════════════════════════════
@mcp.tool()
def rechercher_sources_rag(
    requete: str,
    top_k: int = 5,
    min_score: float = 0.45,
    db_path: Optional[str] = None,
) -> dict[str, Any]:
    """
    Interroge le Vector Store SQLite persistant de Bourbon.IA (`data/bourbon_rag.db`).
    Grounding strict : retourne les extraits sourcés avec références exactes, ou
    strictement `"Information non disponible dans les sources"` si aucun document ne correspond.
    """
    store = PersistentRAGStore(db_path=db_path) if db_path else get_default_rag_store()
    return query_rag(question=requete, top_k=top_k, min_score=min_score, store=store)


# ══════════════════════════════════════════════════════════════════════════
# OUTIL MCP 4 : generer_prejaune_rtf
# ══════════════════════════════════════════════════════════════════════════
def _rtf_escape_py(text: str) -> str:
    out: list[str] = []
    for ch in str(text or ""):
        code = ord(ch)
        if ch in ("\\", "{", "}"):
            out.append("\\" + ch)
        elif code < 128:
            out.append(ch)
        else:
            signed = code - 65536 if code > 32767 else code
            out.append(f"\\u{signed}?")
    return "".join(out)


@mcp.tool()
def generer_prejaune_rtf(amendements_json: str | list[dict[str, Any]] | dict[str, Any]) -> str:
    """
    Génère le document RTF au format « préjaune » de l'Assemblée nationale
    avec crochets (`╓ ║ ╙`) et mentions `[Id.]` / `[Dc.]` prêt pour la séance.
    """
    raw_list = _parse_amendements_input(amendements_json)
    _, items = _executer_pipeline_mecanique(raw_list)

    parts = [
        "{\\rtf1\\ansi\\ansicpg1252\\deff0",
        "{\\fonttbl{\\f0\\froman\\fcharset0 Times New Roman;}}",
        "\\paperw11907\\paperh16840\\margl1843\\margr1418\\margt850\\margb567",
        "\\pard\\qc\\f0\\fs24\\b Version provisoire du pr\\u233?-jaune\\b0\\par",
        f"\\pard\\qc\\f0\\fs18\\i G\\u233?n\\u233?r\\u233? le {datetime.now().strftime('%d/%m/%Y')} \\u8212? Dc. = discussion commune, Id. = identiques\\i0\\par\\par",
    ]

    last_header = None
    n = len(items)
    for idx, a in enumerate(items):
        article = str(a.get("article") or "")
        header = f"ARTICLE {article}" if not article.upper().startswith("ARTICLE") else article.upper()
        if header != last_header:
            if last_header is not None:
                parts.append("\\par")
            parts.append(f"\\pard\\f0\\fs24\\b {_rtf_escape_py(header)}\\b0\\par")
            last_header = header

        res_ia = a.get("resultat_ia") or {}
        statut = res_ia.get("statut") or a.get("statut") or ""
        grp = res_ia.get("groupe") or {}
        gid = grp.get("groupe_id") or a.get("groupe_identique_id")

        prefix = ""
        label = ""
        glyph = ""
        if statut in ("Discussion commune", "Incompatible", "Similaire"):
            prefix = "\\b [Dc.]\\b0  "
        elif statut in ("Identique", "Identiques"):
            prefix = "\\b [Id.]\\b0  "

        if gid:
            prev_gid = (
                ((items[idx - 1].get("resultat_ia") or {}).get("groupe") or {}).get("groupe_id")
                or items[idx - 1].get("groupe_identique_id")
                if idx > 0
                else None
            )
            next_gid = (
                ((items[idx + 1].get("resultat_ia") or {}).get("groupe") or {}).get("groupe_id")
                or items[idx + 1].get("groupe_identique_id")
                if idx + 1 < n
                else None
            )
            if prev_gid != gid:
                glyph = "╓"
                label = "Id." if statut in ("Identique", "Identiques") else "Dc."
            elif next_gid != gid:
                glyph = "╙"
            else:
                glyph = "║"

        auteurs_list = a.get("auteurs") or []
        auteurs_text = ", ".join(str(x) for x in auteurs_list) if auteurs_list else "la commission"
        numero = a.get("numero") or a.get("id") or ""
        raw_content = f"Adt n\u00b0 {numero} de {auteurs_text}"
        escaped_content = prefix + _rtf_escape_py(raw_content)

        line_str = (
            "\\tab \\tab \\tab "
            + (_rtf_escape_py(label) if label else "")
            + "\\tab "
            + (_rtf_escape_py(glyph + " ") if glyph else "")
            + "\\tab "
            + escaped_content
        )
        parts.append(f"\\pard\\f0\\fs22\\tx851\\tx1321\\tx1985 {line_str}\\par")

    parts.append("}")
    return "\n".join(parts)


# ══════════════════════════════════════════════════════════════════════════
# OUTIL MCP 5 : evaluer_regles_irrecevabilite
# ══════════════════════════════════════════════════════════════════════════
@mcp.tool()
def evaluer_regles_irrecevabilite(
    amendement_json: str | dict[str, Any],
    texte_loi_global: str = "",
    db_path: Optional[str] = None,
) -> dict[str, Any]:
    """
    Évalue un amendement contre le catalogue des 384 règles d'irrecevabilité
    (Article 40 C., Article 45 C. Cavalier législatif, Article 98 RAN Ordre d'appel).
    """
    am = json.loads(amendement_json) if isinstance(amendement_json, str) else amendement_json
    engine = LegislativeRulesEngine(db_path=db_path) if db_path else get_default_rules_engine()
    rag = PersistentRAGStore(db_path=db_path) if db_path else get_default_rag_store()
    return evaluate_amendment_rules(
        amendement=am,
        texte_loi_global=texte_loi_global or None,
        rag_store=rag,
        engine=engine,
    )


# ══════════════════════════════════════════════════════════════════════════
# OUTIL MCP 6 : verifier_influence_hatvp
# ══════════════════════════════════════════════════════════════════════════
@mcp.tool()
def verifier_influence_hatvp(
    amendement_json: str | dict[str, Any],
    db_path: Optional[str] = None,
) -> dict[str, Any]:
    """
    Croise un amendement avec le graphe local des déclarations de représentants
    d'intérêts HATVP et retourne les correspondances sourcées.
    """
    am = json.loads(amendement_json) if isinstance(amendement_json, str) else amendement_json
    store = HATVPGraphStore(db_path=db_path) if db_path else get_default_hatvp_store()
    return check_amendment_influence(amendement=am, store=store)


# ══════════════════════════════════════════════════════════════════════════
# OUTIL MCP 7 : debunker_historique_acteur
# ══════════════════════════════════════════════════════════════════════════
@mcp.tool()
def debunker_historique_acteur(
    amendement_json: str | dict[str, Any],
    db_path: Optional[str] = None,
) -> dict[str, Any]:
    """
    Vérifie l'historique des scrutins et interventions de l'auteur ou de son groupe
    pour détecter les contradictions chronologiques (ou retourne strictement
    'Information non disponible dans les sources' si aucun historique n'existe).
    """
    am = json.loads(amendement_json) if isinstance(amendement_json, str) else amendement_json
    store = ChronoDebunkerStore(db_path=db_path) if db_path else get_default_debunker_store()
    return check_actor_chronology(amendement=am, store=store)


if __name__ == "__main__":
    mcp.run()
