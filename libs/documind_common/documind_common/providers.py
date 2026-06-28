"""Provider-pluggable LLM + embeddings.

Callers import only `get_chat_model()` and `get_embeddings()` and never reference
a concrete provider class — so switching the chat model is a config change
(LLM_PROVIDER) plus one dependency, with zero changes elsewhere. This is the
LangChain equivalent of Spring AI's `ChatModel`/`EmbeddingModel` interfaces.
"""
from __future__ import annotations

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from documind_common.config import settings


def get_embeddings() -> Embeddings:
    """Return the embeddings model for the configured provider.

    OpenAI for openai/anthropic (Anthropic has no embeddings API, so it borrows
    OpenAI's); Ollama for the fully-local, free setup. Every stored vector must
    come from the same model the queries use — and different models have
    different dimensions, so switching providers needs a fresh collection
    (see docs/ai/local-ollama.md)."""
    if settings.llm_provider.lower() == "ollama":
        from langchain_ollama import OllamaEmbeddings  # optional dependency

        return OllamaEmbeddings(
            model=settings.embedding_model,
            base_url=settings.ollama_base_url,
        )

    return OpenAIEmbeddings(
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )


def get_chat_model() -> BaseChatModel:
    """Return the configured chat model. streaming=True so the ask flow can
    stream tokens to the browser."""
    provider = settings.llm_provider.lower()

    if provider == "openai":
        return ChatOpenAI(
            model=settings.chat_model,
            temperature=settings.temperature,
            streaming=True,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
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

    # ---- FULLY LOCAL / FREE via Ollama (no API key, runs in Docker) ----
    # docker compose --profile ollama up -d ollama && make ollama-pull
    # then set LLM_PROVIDER=ollama (see docs/ai/local-ollama.md).
    if provider == "ollama":
        from langchain_ollama import ChatOllama  # local import: optional dependency

        return ChatOllama(
            model=settings.chat_model,
            temperature=settings.temperature,
            base_url=settings.ollama_base_url,
        )

    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider!r}")
