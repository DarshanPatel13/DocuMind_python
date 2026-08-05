"""Grounded prompt construction and the no-information sentinel.

Hallucination control lives here plus in config (temperature 0.2) and in the
ask service (the empty-retrieval short-circuit).
"""
from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

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


WHOLE_DOC_NOTE = (
    "\nThe context below is the COMPLETE document (every section, in order). When the "
    "user asks you to list, enumerate, summarize, or give an overview, be EXHAUSTIVE: "
    "include every relevant item and do not omit any. Do not invent items not present."
)


def build_messages(
    question: str,
    docs: list[Document],
    *,
    whole_document: bool = False,
    history: list[tuple[str, str]] | None = None,
) -> list[BaseMessage]:
    """Grounded prompt, optionally preceded by recent conversation turns.

    History is replayed as real Human/AI message pairs rather than pasted into
    the user message, so the model sees turn structure the way it was trained on
    it, and so the grounding rules stay clearly separated from conversational
    context. The retrieved context still governs the answer: prior turns exist to
    resolve references like "it" and "that", not to be cited as sources."""
    system = SYSTEM_PROMPT + (WHOLE_DOC_NOTE if whole_document else "")
    messages: list[BaseMessage] = [SystemMessage(content=system)]

    for prev_question, prev_answer in history or []:
        messages.append(HumanMessage(content=prev_question))
        messages.append(AIMessage(content=prev_answer))

    messages.append(
        HumanMessage(content=f"Context:\n{build_context(docs)}\n\nQuestion: {question}")
    )
    return messages
