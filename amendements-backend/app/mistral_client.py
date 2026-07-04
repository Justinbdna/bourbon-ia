import json
import logging

import httpx

from app.config import Settings

logger = logging.getLogger("amendements.mistral")


class MistralError(Exception):
    """Erreur lors de l'appel à l'API Mistral (réseau, auth, quota...)."""


class MistralInvalidJSONError(Exception):
    """Le modèle n'a pas renvoyé de JSON exploitable après plusieurs tentatives."""


async def call_mistral_for_classification(
    settings: Settings,
    system_prompt: str,
    user_prompt: str,
) -> dict:
    """
    Appelle l'API Mistral en mode "chat completion" avec sortie JSON forcée
    (response_format json_object), et retente en cas de JSON invalide.
    """
    headers = {
        "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
        "Content-Type": "application/json",
    }

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    last_error: Exception | None = None

    async with httpx.AsyncClient(timeout=settings.MISTRAL_TIMEOUT) as client:
        for attempt in range(1, settings.MAX_JSON_RETRIES + 2):  # 1 essai + N retries
            body = {
                "model": settings.MISTRAL_MODEL,
                "messages": messages,
                "temperature": 0.1,  # faible : on veut un classement déterministe, pas créatif
                "response_format": {"type": "json_object"},
            }

            try:
                response = await client.post(settings.MISTRAL_API_URL, headers=headers, json=body)
            except httpx.HTTPError as exc:
                raise MistralError(f"Erreur réseau lors de l'appel à Mistral : {exc}") from exc

            if response.status_code == 401:
                raise MistralError("Clé API Mistral invalide ou manquante (401).")
            if response.status_code == 429:
                raise MistralError("Limite de requêtes Mistral atteinte (429). Réessaie dans un instant.")
            if response.status_code >= 400:
                raise MistralError(
                    f"Erreur Mistral ({response.status_code}) : {response.text[:500]}"
                )

            data = response.json()
            try:
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                return parsed
            except (KeyError, IndexError, json.JSONDecodeError) as exc:
                last_error = exc
                logger.warning(
                    "Réponse Mistral non exploitable (tentative %s/%s) : %s",
                    attempt,
                    settings.MAX_JSON_RETRIES + 1,
                    exc,
                )
                # On renforce la consigne pour la tentative suivante.
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Ta précédente réponse n'était pas un JSON valide respectant le "
                            "format demandé. Renvoie uniquement le JSON, sans aucun autre texte."
                        ),
                    }
                )
                continue

    raise MistralInvalidJSONError(
        f"Le modèle n'a pas renvoyé de JSON exploitable après plusieurs tentatives : {last_error}"
    )
