"""document-service configuration — only what THIS service owns.

The shared pgvector/provider settings live in `documind_common.config`; here we
add the things document-service alone is responsible for: where PDFs are stored,
the upload size limit, and its Kafka topics/consumer group.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ---- Postgres (the `documents` metadata table, async/asyncpg) ----
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "documind"
    postgres_user: str = "documind"
    postgres_password: str = "documind"

    # ---- Kafka ----
    kafka_bootstrap_servers: str = "localhost:9092"
    document_events_topic: str = "document-events"
    document_events_dlt_topic: str = "document-events.DLT"
    consumer_group: str = "documind-ingestion"

    # ---- Uploads ----
    storage_dir: str = "./storage"
    max_upload_bytes: int = 20 * 1024 * 1024

    @property
    def sqlalchemy_async_url(self) -> str:
        """Async engine (asyncpg) for the `documents` metadata table."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
