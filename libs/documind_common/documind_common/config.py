"""Shared RAG configuration, loaded once from environment / .env.

Only the settings that the shared plumbing needs live here — the LLM/embeddings
provider and the pgvector connection. Each service has its OWN config module for
the things it alone owns (storage paths, Kafka topics, Mongo URI, JWT secret).

pydantic-settings reads from the environment, so every service container just
sets the same env vars and this picks them up — no config has to be passed in.

Java analogy: like a shared `@ConfigurationProperties` for cross-cutting infra,
with each service adding its own properties on top.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class CommonSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ---- LLM / embeddings provider ----
    openai_api_key: str = "sk-missing"
    openai_base_url: str | None = None
    anthropic_api_key: str = ""
    llm_provider: str = "openai"          # "openai" | "anthropic" (chat only)
    chat_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    temperature: float = 0.2

    # ---- Postgres / pgvector (the SHARED vector store) ----
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "documind"
    postgres_user: str = "documind"
    postgres_password: str = "documind"

    # ---- RAG / chunking (writer + reader must agree on collection) ----
    chunk_size_tokens: int = 800
    overlap_tokens: int = 100
    chars_per_token: int = 4
    top_k: int = 4
    vector_collection: str = "documind_chunks"

    @property
    def pgvector_url(self) -> str:
        """Connection string PGVector uses (psycopg3 driver)."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> CommonSettings:
    return CommonSettings()


settings = get_settings()
