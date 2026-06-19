"""Application configuration, loaded once from environment / .env.

Pydantic-settings gives the same type-safe, validated config that Spring's
@ConfigurationProperties does — every setting has a type, a default, and is
read from the environment exactly once at import time.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ---- OpenAI / provider ----
    openai_api_key: str = "sk-missing"
    anthropic_api_key: str = ""
    llm_provider: str = "openai"          # "openai" | "anthropic" (chat only)
    chat_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    temperature: float = 0.2

    # ---- Postgres ----
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "documind"
    postgres_user: str = "documind"
    postgres_password: str = "documind"

    # ---- MongoDB ----
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "documind"

    # ---- Kafka ----
    kafka_bootstrap_servers: str = "localhost:9092"
    document_events_topic: str = "document-events"
    document_events_dlt_topic: str = "document-events.DLT"
    consumer_group: str = "documind-ingestion"

    # ---- RAG / chunking ----
    chunk_size_tokens: int = 800
    overlap_tokens: int = 100
    chars_per_token: int = 4               # heuristic: ~4 chars per token of English
    top_k: int = 4

    # ---- App ----
    storage_dir: str = "./storage"
    max_upload_bytes: int = 20 * 1024 * 1024
    cors_origins: str = "http://localhost:5173"
    rate_limit_per_minute: int = 10
    vector_collection: str = "documind_chunks"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sqlalchemy_async_url(self) -> str:
        """Async engine (asyncpg) for the `documents` metadata table."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def pgvector_url(self) -> str:
        """Connection string PGVector uses (psycopg3 driver)."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Cached so the env is parsed once; import this everywhere."""
    return Settings()


settings = get_settings()
