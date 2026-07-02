"""
Test automatisé — Vérification du mapping Qwen 35B et du timeout 300s.
Envoie un payload massif à POST /api/chat avec le modèle Expert (Qwen 35B).
"""
import requests
import time

API_URL = "http://127.0.0.1:8000/api/chat"

payload = {
    "message": "Fais un résumé",
    "context_text": "Ceci est un test de timeout. " * 500,
    "model": "🧠 Bourbon Expert (Qwen 35B)",
}

print("=" * 60)
print("🧪 TEST AUTOMATISÉ — Mapping Qwen 35B + Timeout 300s")
print(f"📡 URL cible : {API_URL}")
print(f"🧠 Modèle demandé : {payload['model']}")
print(f"📎 Taille du contexte : {len(payload['context_text'])} caractères")
print("=" * 60)
print("\n⏳ Envoi en cours (patience, Qwen 35B peut prendre du temps)...\n")

start = time.time()

try:
    response = requests.post(API_URL, json=payload, timeout=300)
    elapsed = time.time() - start

    print(f"⏱️  Temps de réponse : {elapsed:.1f} secondes")
    print(f"📬 Status HTTP : {response.status_code}")

    if response.ok:
        data = response.json()
        print("\n✅ SUCCÈS — Réponse du LLM :")
        print("-" * 40)
        print(data.get("content", "(vide)"))
        print("-" * 40)
    else:
        print(f"\n❌ ÉCHEC — Détail : {response.text}")

except requests.exceptions.Timeout:
    elapsed = time.time() - start
    print(f"\n❌ TIMEOUT après {elapsed:.1f}s — Le serveur n'a pas répondu dans les 300s.")
except requests.exceptions.ConnectionError:
    print("\n❌ CONNEXION REFUSÉE — Le serveur FastAPI est-il démarré ?")
except Exception as e:
    print(f"\n❌ ERREUR INATTENDUE : {e}")
