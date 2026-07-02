"""
Centralized application settings.

Design decision: we use pydantic-settings instead of raw os.environ reads so that
every environment variable is validated once, at startup, with a clear error if
something required is missing. This avoids the common failure mode of a typo'd
env var silently becoming `None` deep inside a service class.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    APP_NAME: str = "WhatsApp AI Platform"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- Security / Auth ---
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12  # 12 hours
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # --- CORS ---
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    # --- MongoDB ---
    MONGO_URI: str
    MONGO_DB_NAME: str = "whatsapp_ai_platform"

    # --- OpenAI ---
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"

    # --- Meta / WhatsApp Cloud API ---
    META_APP_SECRET: str = ""
    META_VERIFY_TOKEN: str = ""
    WHATSAPP_API_VERSION: str = "v20.0"
    WHATSAPP_GRAPH_BASE_URL: str = "https://graph.facebook.com"

    # --- Media ---
    MEDIA_STORAGE_DIR: str = "./media_storage"
    MAX_MEDIA_SIZE_MB: int = 16

    # --- Agent behavior ---
    AGENT_MAX_RETRIES: int = 2
    AGENT_LOW_CONFIDENCE_THRESHOLD: float = 0.55  # below this -> human handoff
    AGENT_SESSION_TTL_HOURS: int = 24

    # --- Logging ---
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """
    Settings are cached (lru_cache) because constructing them re-reads and
    re-validates the .env file, which is wasted work if done per-request.
    FastAPI's dependency injection makes this cache-and-inject pattern free
    to use via `Depends(get_settings)`.
    """
    return Settings()
