import json
import html
import re
import logging
import argparse
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def strip_html(texte: str) -> str:
    """Supprime les balises HTML et décode les entités (ex: &#x00E8; → è)."""
    if not texte:
        return ""
    sans_balises = re.sub(r"<[^>]+>", "", texte)
    return html.unescape(sans_balises).strip()

def clean_amendement(amendement_brut):
    """
    Extrait les champs pertinents d'un amendement brut de l'Assemblée nationale.
    Structure basée sur l'Open Data de l'Assemblée.
    """
    # 1. Numéro de l'amendement (souvent dans uid ou numeroLong)
    numero = amendement_brut.get("numeroLong", amendement_brut.get("uid", "Inconnu"))
    
    # 2. Auteur / Signataires
    signataires = amendement_brut.get("signataires", {})
    auteur = "Auteur inconnu"
    if "libelle" in signataires:
        auteur = strip_html(signataires.get("libelle", "")) or "Auteur inconnu"
    elif "auteur" in signataires:
        auteur = strip_html(signataires["auteur"].get("acteurRef", "")) or "Auteur inconnu"

    # 3. Textes (Dispositif = le changement de loi, Exposé sommaire = la justification)
    corps = amendement_brut.get("corps", {})
    contenu_auteur = corps.get("contenuAuteur", {})
    
    dispositif = strip_html(contenu_auteur.get("dispositif", "")) or "Texte non disponible"
    expose_sommaire = strip_html(contenu_auteur.get("exposeSommaire", "")) or "Exposé des motifs non disponible"

    return {
        "numero": numero,
        "auteur": auteur,
        "texte": dispositif,
        "motif": expose_sommaire
    }

def load_single_json(filepath: str) -> dict | None:
    """Charge un fichier JSON unique et retourne l'amendement nettoyé, ou None."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"JSON corrompu — {filepath} : {e}")
        return None
    except OSError as e:
        logging.error(f"Lecture impossible — {filepath} : {e}")
        return None

    # L'Open Data wrape chaque amendement dans {"amendement": {...}}
    if "amendement" in data:
        return clean_amendement(data["amendement"])
    # Fallback : fichier plat
    return clean_amendement(data)


def process_directory(input_dir: str, output_path: str) -> list | None:
    """
    Parcourt récursivement un dossier de JSON (1 fichier = 1 amendement).
    Retourne la liste des amendements nettoyés et la sauvegarde dans output_path.
    """
    input_dir = Path(input_dir)
    if not input_dir.is_dir():
        logging.error(f"Dossier introuvable : {input_dir}")
        return None

    fichiers = sorted(input_dir.rglob("*.json"))
    logging.info(f"{len(fichiers)} fichiers JSON trouvés dans {input_dir}")

    if not fichiers:
        logging.warning("Aucun fichier JSON trouvé.")
        return []

    resultats = []
    erreurs = 0
    for f in fichiers:
        amendement = load_single_json(str(f))
        if amendement:
            resultats.append(amendement)
        else:
            erreurs += 1

    logging.info(f"Nettoyage terminé : {len(resultats)} ok, {erreurs} erreurs.")

    # Sauvegarder
    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(resultats, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logging.error(f"Écriture impossible — {output_path} : {e}")
        return None

    logging.info(f"Fichier allégé sauvegardé : {output_path}")
    return resultats


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Parser les JSON d'amendements de l'Assemblée nationale")
    p.add_argument("--input-dir", required=True, help="Dossier racine contenant les JSON bruts")
    p.add_argument("--output", required=True, help="Chemin vers le JSON de destination allégé")

    args = p.parse_args()
    process_directory(args.input_dir, args.output)
