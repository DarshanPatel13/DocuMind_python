"""gateway configuration: auth, rate limiting, and where to route.

The gateway is the only service exposed to the browser. It owns a tiny `users`
table (in the shared Postgres) for login, a JWT signing secret, a Redis-backed
rate limiter, and the upstream URLs of the internal services.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ---- JWT ----
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # ---- Seeded demo user (created on startup if absent) ----
    demo_username: str = "demo"
    demo_password: str = "demo12345"

    # ---- Redis (rate limiting) ----
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_per_minute: int = 10

    # ---- Upstream services ----
    document_service_url: str = "http://localhost:8001"
    query_service_url: str = "http://localhost:8002"

    # ---- CORS (the browser origin) ----
    cors_origins: str = "http://localhost:5173"

    # ---- Postgres (the `users` table, async/asyncpg) ----
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "documind"
    postgres_user: str = "documind"
    postgres_password: str = "documind"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sqlalchemy_async_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
