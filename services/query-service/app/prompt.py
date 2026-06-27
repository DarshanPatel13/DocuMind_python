"""Grounded prompt construction and the no-information sentinel.

Hallucination control lives here plus in config (temperature 0.2) and in the
ask service (the empty-retrieval short-circuit).
"""
from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

# Exact string the model is told to return when the context has no answer.
# Exact, because exact strings are testable and detectable downstream.
NO_INFO_ANSWER = "I don't have enough information in the uploaded documents."

SYSTEM_PROMPT = (
    "You are DocuMind, an assistant that answers questions about the user's "
    "uploaded documents.\n"
    "Answer ONLY from the context provided in the user message.\n"
    "Cite sources as [filename, chunk N] after the statements they support.\n"
    "If the context does not contain the answer, reply exactly:\n"
    f"{NO_INFO_ANSWER}"
)


def build_context(docs: list[Document]) -> str:
    """Render retrieved chunks, each labelled exactly the way the model is told
    to cite it."""
    blocks = [
        f"[{doc.metadata.get('filename', 'unknown')}, "
        f"chunk {doc.metadata.get('chunk_index', 0)}]\n{doc.page_content}"
        for doc in docs
    ]
    return "\n---\n".join(blocks)


def build_messages(question: str, docs: list[Document]) -> list[BaseMessage]:
    user = f"Context:\n{build_context(docs)}\n\nQuestion: {question}"
    return [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user)]
