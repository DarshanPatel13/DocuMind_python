"""Langfuse LLM observability.

Returns a LangChain callback handler that traces every LLM call — prompt,
token counts, cost, and latency — to Langfuse. It is a **no-op unless
LANGFUSE_PUBLIC_KEY is set**, so the default `docker compose up` runs without
any observability backend; you opt in by starting Langfuse and setting keys.

Why callbacks: LangChain runs emit lifecycle events (on_llm_start/-end, …).
Langfuse's handler subscribes to them, so we get traces without changing the
ask logic — we just pass the handler in the call's `config`.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.config import settings


@lru_cache
def get_langfuse_handler() -> Any | None:
    if not settings.langfuse_public_key:
        return None
    from langfuse.callback import CallbackHandler

    return CallbackHandler(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )
