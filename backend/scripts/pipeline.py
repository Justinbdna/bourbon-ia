"""
Pipeline Bourbon.IA — Chaîne complète : Parser → Scanner
Charge les amendements nettoyés et les envoie au LLM un par un.

Usage :
  python3 pipeline.py --clean data/clean/amendements_clean.json --limit 3
"""
import json
import logging
import argparse
from pathlib import Path

from scanner import resumer_amendement

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def run_pipeline(clean_path: str, output_path: str, limit: int | None = None):
    """
    Charge les amendements nettoyés et les scanne via le LLM.
    
    Args:
        clean_path: chemin vers le JSON nettoyé (sortie de parser.py)
        output_path: chemin de sauvegarde des résumés
        limit: nombre max d'amendements à scanner (None = tous)
    """
    # 1. Charger les données nettoyées
    logging.info(f"Chargement de {clean_path}...")
    try:
        with open(clean_path, "r", encoding="utf-8") as f:
            amendements = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logging.error(f"Impossible de charger {clean_path} : {e}")
        return

    total = len(amendements)
    if limit:
        amendements = amendements[:limit]
    logging.info(f"{len(amendements)}/{total} amendements sélectionnés pour le scan.")

    # 2. Scanner chaque amendement via le LLM
    resultats = []
    for i, am in enumerate(amendements, 1):
        logging.info(f"[{i}/{len(amendements)}] Scan de l'amendement {am.get('numero', '?')}...")
        resume = resumer_amendement(am)
        if resume:
            resultats.append(resume)
        else:
            logging.warning(f"Échec du scan pour {am.get('numero', '?')}")

    # 3. Sauvegarder les résultats
    logging.info(f"Scan terminé : {len(resultats)}/{len(amendements)} résumés générés.")

    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(resultats, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logging.error(f"Écriture impossible — {output_path} : {e}")
        return None

    logging.info(f"Résultats sauvegardés : {output_path}")
    return resultats


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Pipeline Bourbon.IA : Parser → Scanner")
    p.add_argument("--clean", required=True,
                    help="Chemin vers le JSON nettoyé (sortie de parser.py)")
    p.add_argument("--output", default="data/clean/resumes.json",
                    help="Chemin de sortie des résumés (défaut: data/clean/resumes.json)")
    p.add_argument("--limit", type=int, default=None,
                    help="Nombre max d'amendements à scanner (défaut: tous)")

    args = p.parse_args()
    run_pipeline(args.clean, args.output, args.limit)
