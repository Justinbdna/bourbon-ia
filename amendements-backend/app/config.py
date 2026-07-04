from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
RULES_PATH = BASE_DIR / "data" / "theorie_classement.md"


class Settings(BaseSettings):
    """
    Paramètres de l'application, lus depuis les variables d'environnement
    ou un fichier .env à la racine du projet backend.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Clé API Mistral — jamais commitée, toujours fournie via .env
    MISTRAL_API_KEY: str

    # Modèle Mistral utilisé pour le classement.
    # mistral-large-latest : meilleure qualité de raisonnement (recommandé pour le classement).
    # mistral-small-latest : plus rapide/économique, utile si le volume d'amendements est élevé
    # pendant le hackathon.
    MISTRAL_MODEL: str = "mistral-large-latest"

    MISTRAL_API_URL: str = "https://api.mistral.ai/v1/chat/completions"

    # Origines autorisées pour le front React (CORS)
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Nombre de tentatives si le modèle renvoie un JSON invalide
    MAX_JSON_RETRIES: int = 2

    # Timeout des appels à l'API Mistral (secondes)
    MISTRAL_TIMEOUT: float = 90.0


@lru_cache
def get_settings() -> "Settings":
    return Settings()


def load_rules_text() -> str:
    """Charge la théorie du classement depuis le fichier markdown dédié.

    Garder ces règles dans un fichier séparé (plutôt qu'en dur dans le code)
    permet de les faire évoluer sans toucher à la logique applicative.
    """
    return RULES_PATH.read_text(encoding="utf-8")
