import json
import logging
import argparse
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

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
        auteur = signataires.get("libelle", "Auteur inconnu")
    elif "auteur" in signataires:
        auteur = signataires["auteur"].get("acteurRef", "Auteur inconnu")

    # 3. Textes (Dispositif = le changement de loi, Exposé sommaire = la justification)
    corps = amendement_brut.get("corps", {})
    contenu_auteur = corps.get("contenuAuteur", {})
    
    dispositif = contenu_auteur.get("dispositif", "Texte non disponible")
    expose_sommaire = contenu_auteur.get("exposeSommaire", "Exposé des motifs non disponible")

    return {
        "numero": numero,
        "auteur": auteur,
        "texte": dispositif,
        "motif": expose_sommaire
    }

def process_file(input_path, output_path):
    logging.info(f"Lecture du fichier massif : {input_path}")

    # 1. Vérifier que le fichier source existe
    if not Path(input_path).is_file():
        logging.error(f"Fichier introuvable : {input_path}")
        return None

    # 2. Charger le JSON avec gestion d'erreur ciblée
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"JSON invalide ou corrompu dans {input_path} : {e}")
        return None
    except OSError as e:
        logging.error(f"Erreur de lecture du fichier {input_path} : {e}")
        return None

    # 3. Extraire la liste d'amendements
    if isinstance(data, dict):
        amendements_bruts = data.get("amendements", [])
    else:
        amendements_bruts = data

    amendements_nettoyes = [clean_amendement(a) for a in amendements_bruts]
    logging.info(f"Nettoyage terminé : {len(amendements_nettoyes)} amendements traités.")

    # 4. Sauvegarder le résultat allégé
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(amendements_nettoyes, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logging.error(f"Impossible d'écrire dans {output_path} : {e}")
        return None

    logging.info(f"Fichier allégé sauvegardé : {output_path}")
    return amendements_nettoyes

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parser et alléger les JSON d'amendements de l'Assemblée nationale")
    parser.add_argument("--input", required=True, help="Chemin vers le JSON source massif")
    parser.add_argument("--output", required=True, help="Chemin vers le JSON de destination allégé")
    
    args = parser.parse_args()
    process_file(args.input, args.output)
