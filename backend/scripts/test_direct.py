import requests

URL = "http://127.0.0.1:8000/api/scan"
AMENDEMENT_ID = "AMANR5L17PO59051B0149P0D1N000001"

print(f"🚀 Envoi de la requête POST à {URL}...")
print(f"📄 Cible : Amendement n° {AMENDEMENT_ID}\n")

try:
    response = requests.post(URL, json={"numero": AMENDEMENT_ID})
    
    if response.status_code == 200:
        data = response.json()
        print("=" * 50)
        print("🎉 RÉPONSE DE L'API FastAPI :")
        print("=" * 50)
        print(f"📌 Numéro : {data.get('numero')}")
        print(f"📌 Source : {data.get('source')}")
        print("\n📝 Résumé :")
        print(data.get('resume'))
        print("\n🔄 Comparatif :")
        print(data.get('comparatif'))
        print("\n🏛️ Enjeux politiques :")
        print(data.get('enjeux_politiques'))
        print("\n⚠️ Points de vigilance :")
        print(data.get('points_de_vigilance'))
        print("\n" + "=" * 50)
    else:
        print(f"❌ Erreur {response.status_code}")
        print(response.text)
        
except requests.exceptions.ConnectionError:
    print("❌ Impossible de se connecter à l'API.")
    print("Vérifiez que le serveur FastAPI tourne bien dans l'autre terminal.")
