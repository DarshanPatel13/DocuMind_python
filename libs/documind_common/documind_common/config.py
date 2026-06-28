"""Shared RAG configuration, loaded once from environment / .env.

Switching providers is a ONE-LINE change: set `LLM_PROVIDER` to `openai`,
`anthropic`, or `ollama`, and the right chat model, embedding model, embedding
dimensions, and vector collection are filled in from a per-provider profile.
Each provider gets its OWN collection (e.g. documind_openai vs documind_ollama),
so you can flip back and forth without the 1536-d/768-d dimension clash and
without re-indexing. Any field can still be overridden explicitly via env.

Java analogy: a shared `@ConfigurationProperties` with Spring profiles — pick the
profile, get its defaults, override individual properties when you need to.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Per-provider defaults. openai/anthropic share OpenAI embeddings (Anthropic has
# none), so they share the 1536-d collection; ollama is fully local at 768-d.
_PROFILES: dict[str, dict] = {
    "openai": {
        "chat_model": "gpt-4o-mini",
        "embedding_model": "text-embedding-3-small",
        "embedding_dimensions": 1536,
        "vector_collection": "documind_openai",
    },
    "anthropic": {
        "chat_model": "claude-sonnet-4-6",
        "embedding_model": "text-embedding-3-small",
        "embedding_dimensions": 1536,
        "vector_collection": "documind_openai",
    },
    "ollama": {
        "chat_model": "llama3.2:3b",
        "embedding_model": "nomic-embed-text",
        "embedding_dimensions": 768,
        "vector_collection": "documind_ollama",
    },
}


class CommonSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ---- Provider switch (the one knob you usually touch) ----
    llm_provider: str = "openai"          # "openai" | "anthropic" | "ollama"

    # ---- Credentials / endpoints ----
    openai_api_key: str = "sk-missing"
    openai_base_url: str | None = None
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    temperature: float = 0.2

    # ---- Model selection (left as None -> derived from the provider profile) ----
    chat_model: str | None = None
    embedding_model: str | None = None
    embedding_dimensions: int | None = None
    vector_collection: str | None = None

    # ---- Postgres / pgvector (the SHARED vector store) ----
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "documind"
    postgres_user: str = "documind"
    postgres_password: str = "documind"

    # ---- RAG / chunking + hybrid retrieval ----
    chunk_size_tokens: int = 800
    overlap_tokens: int = 100
    chars_per_token: int = 4
    top_k: int = 4
    hybrid_enabled: bool = True
    retrieval_candidates: int = 20
    reranker: str = "none"               # "none" | "cross-encoder"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    @model_validator(mode="after")
    def _apply_provider_profile(self) -> "CommonSettings":
        # Treat unset OR empty ("") as "use the provider profile" — empty strings
        # are common when a compose var is passed through without a value.
        profile = _PROFILES.get(self.llm_provider.lower(), _PROFILES["openai"])
        if not self.chat_model:
            self.chat_model = profile["chat_model"]
        if not self.embedding_model:
            self.embedding_model = profile["embedding_model"]
        if not self.embedding_dimensions:
            self.embedding_dimensions = profile["embedding_dimensions"]
        if not self.vector_collection:
            self.vector_collection = profile["vector_collection"]
        return self

    @property
    def pgvector_url(self) -> str:
        """Connection string PGVector uses (SQLAlchemy + psycopg3 driver)."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def psycopg_conninfo(self) -> str:
        """Plain libpq DSN for raw psycopg queries (the keyword-search arm)."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> CommonSettings:
    return CommonSettings()


settings = get_settings()
