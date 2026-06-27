"""query-service configuration — only what THIS service owns.

The shared pgvector/provider/top_k settings live in `documind_common.config`;
here we add the MongoDB connection for conversation history.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ---- MongoDB (conversation history) ----
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "documind"

    # ---- Langfuse LLM observability (no-op unless a public key is set) ----
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
