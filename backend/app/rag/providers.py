"""Provider-pluggable LLM + embeddings.

The rest of the app imports only `get_chat_model()` and `get_embeddings()` and
never references a concrete provider class — so switching the chat model is a
config change (LLM_PROVIDER) plus one dependency, with zero changes elsewhere.
This is the LangChain equivalent of the Java version's Spring AI interfaces.
"""
from __future__ import annotations

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import settings


def get_embeddings() -> Embeddings:
    """Embeddings ALWAYS come from OpenAI — Anthropic has no embeddings API,
    and every stored vector must come from the same model the queries use."""
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
        api_key=settings.openai_api_key,
    )


def get_chat_model() -> BaseChatModel:
    """Return the configured chat model. streaming=True so /api/ask can stream
    tokens to the browser."""
    provider = settings.llm_provider.lower()

    if provider == "openai":
        return ChatOpenAI(
            model=settings.chat_model,
            temperature=settings.temperature,
            streaming=True,
            api_key=settings.openai_api_key,
        )

    # ---- SWITCHING THE CHAT MODEL TO ANTHROPIC CLAUDE ----
    # 1. pip install langchain-anthropic
    # 2. set LLM_PROVIDER=anthropic, CHAT_MODEL=claude-sonnet-4-6, ANTHROPIC_API_KEY=...
    # Nothing else changes — embeddings stay on OpenAI above.
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic  # local import: optional dependency

        return ChatAnthropic(
            model=settings.chat_model,
            temperature=settings.temperature,
            streaming=True,
            api_key=settings.anthropic_api_key,
        )

    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider!r}")
