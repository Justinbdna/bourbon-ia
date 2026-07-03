import httpx
import json

def test_streaming():
    url = "http://127.0.0.1:8000/api/chat"
    payload = {
        "message": "Quel est le dernier amendement à ce jour ?",
        "context_text": "",
        "model": "mac_mistral"
    }

    try:
        print(f"🚀 Lancement du test sur {url}...")
        with httpx.stream("POST", url, json=payload, timeout=60.0) as response:
            if response.status_code != 200:
                print(f"❌ Erreur {response.status_code}")
                print(response.read().decode())
                return

            print("✅ Connexion réussie, lecture du flux SSE...\n")
            full_response = ""
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        if "content" in data:
                            chunk = data["content"]
                            print(chunk, end="", flush=True)
                            full_response += chunk
                    except json.JSONDecodeError:
                        pass
            print("\n\n🎉 Test terminé avec succès.")
    except Exception as e:
        print(f"❌ Exception lors du test : {e}")

if __name__ == "__main__":
    test_streaming()
