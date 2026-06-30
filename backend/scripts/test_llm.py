import os
from openai import OpenAI

# LM Studio expose une API locale compatible avec OpenAI (port 1234 par défaut)
client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"  # Clé factice, requise par le SDK mais ignorée par LM Studio
)

def tester_connexion():
    print("⏳ Tentative de connexion à LM Studio...")
    try:
        # Envoi d'une requête de test très basique
        response = client.chat.completions.create(
            model="local-model", # LM Studio utilise automatiquement le modèle que vous avez chargé
            messages=[
                {"role": "system", "content": "Tu es Bourbon.IA, un assistant législatif expert."},
                {"role": "user", "content": "Bonjour, es-tu prêt à analyser des amendements ? Réponds brièvement."}
            ],
            temperature=0.7
        )
        print("✅ Connexion réussie ! Voici la réponse du LLM local :")
        print(f"\n> {response.choices[0].message.content}\n")
        
    except Exception as e:
        print("❌ Erreur de connexion à LM Studio.")
        print("Vérifiez que :")
        print("1. LM Studio est bien ouvert.")
        print("2. Un modèle est chargé.")
        print("3. Le serveur local est démarré (bouton 'Start Server' dans l'onglet Local Server).")
        print(f"\nDétail technique : {e}")

if __name__ == "__main__":
    tester_connexion()
