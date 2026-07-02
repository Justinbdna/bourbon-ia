import json
import logging
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Connexion au LLM local via LM Studio (API compatible OpenAI)
client = OpenAI(
    base_url="http://127.0.0.1:1234/v1",
    api_key="lm-studio"
)

# Identifiant du modèle chargé dans LM Studio
MODEL_ID = "mistralai/mistral-7b-instruct-v0.3"

SYSTEM_PROMPT = (
    "Tu es Bourbon.IA, un assistant législatif expert de l'Assemblée nationale française. "
    "Tu résumes les amendements de manière structurée et factuelle. "
    "Tu ne dois JAMAIS inventer d'information. Si une donnée est absente, "
    "réponds strictement : 'Information non disponible dans les sources'."
)


def resumer_amendement(amendement_clean: dict) -> dict:
    """
    Envoie un amendement nettoyé au LLM local et retourne un résumé structuré.
    
    Args:
        amendement_clean: dict issu de parser.clean_amendement()
            Clés attendues : numero, auteur, texte, motif
    
    Returns:
        dict avec les clés : numero, resume, enjeux, source
        ou None en cas d'erreur.
    """
    numero = amendement_clean.get("numero", "Inconnu")

    # Construction du prompt utilisateur
    user_prompt = (
        f"Voici l'amendement n°{numero} :\n\n"
        f"**Auteur** : {amendement_clean.get('auteur', 'Non renseigné')}\n\n"
        f"**Dispositif (texte de loi modifié)** :\n{amendement_clean.get('texte', 'Non disponible')}\n\n"
        f"**Exposé des motifs** :\n{amendement_clean.get('motif', 'Non disponible')}\n\n"
        "Fournis un résumé structuré avec :\n"
        "1. **Résumé** : 2-3 phrases claires sans jargon.\n"
        "2. **Enjeux** : les implications juridiques et politiques principales.\n"
        "3. **Source** : rappelle le numéro de l'amendement analysé."
    )

    logging.info(f"Envoi de l'amendement n°{numero} au LLM...")

    try:
        # Mistral 7B Instruct n'accepte que user/assistant dans son template Jinja.
        # On injecte le rôle système en tête du message utilisateur.
        full_prompt = f"[INSTRUCTION SYSTÈME] {SYSTEM_PROMPT}\n\n[REQUÊTE]\n{user_prompt}"

        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "user", "content": full_prompt},
            ],
            temperature=0.3,  # Bas pour rester factuel
            max_tokens=512,
        )
    except ConnectionError:
        logging.error("Connexion refusée. LM Studio est-il démarré ?")
        return None
    except Exception as e:
        logging.error(f"Erreur lors de l'appel au LLM : {e}")
        return None

    # Extraire la réponse
    contenu = response.choices[0].message.content
    if not contenu or not contenu.strip():
        logging.warning(f"Réponse vide du LLM pour l'amendement n°{numero}.")
        return None

    logging.info(f"Résumé reçu pour l'amendement n°{numero}.")

    return {
        "numero": numero,
        "resume": contenu.strip(),
        "source": f"Amendement n°{numero}",
    }


if __name__ == "__main__":
    # Test rapide avec un amendement factice
    test_amendement = {
        "numero": "CL42",
        "auteur": "Mme Dupont",
        "texte": "À l'article 3, remplacer les mots « deux ans » par les mots « trois ans ».",
        "motif": "Cet amendement vise à allonger le délai de prescription afin de mieux protéger les victimes.",
    }

    resultat = resumer_amendement(test_amendement)
    if resultat:
        print("\n" + "=" * 50)
        print("RÉSULTAT DU SCANNER")
        print("=" * 50)
        print(resultat["resume"])
        print(f"\n📌 Source : {resultat['source']}")
    else:
        print("❌ Le scan a échoué.")
