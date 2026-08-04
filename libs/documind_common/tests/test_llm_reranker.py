"""The LLM reranker's contract is "reorder, never lose data, never break
retrieval", so these target the parser and the failure paths rather than ranking
quality (which the eval suite measures against the golden dataset)."""
from __future__ import annotations

from unittest.mock import MagicMock

from langchain_core.documents import Document

from documind_common.reranker import LlmReranker


def _docs(*texts: str) -> list[Document]:
    return [Document(page_content=t, metadata={"chunk_id": f"c{i}"}) for i, t in enumerate(texts)]


CANDIDATES = _docs("alpha", "bravo", "charlie", "delta")


def _reranker_replying(reply: str) -> LlmReranker:
    chat = MagicMock()
    chat.invoke.return_value = MagicMock(content=reply)
    return LlmReranker(chat_model=chat)


def _texts(scored) -> list[str]:
    return [doc.page_content for doc, _ in scored]


def test_reorders_candidates_by_the_models_ranking() -> None:
    scored = _reranker_replying("3,1,4,2").rerank("q", CANDIDATES)

    assert _texts(scored) == ["charlie", "alpha", "delta", "bravo"]
    # Scores descend so callers can sort uniformly regardless of backend.
    assert [s for _, s in scored] == sorted((s for _, s in scored), reverse=True)


def test_appends_candidates_the_model_omitted() -> None:
    """A model that drops a passage must not delete it from retrieval."""
    scored = _reranker_replying("2,1").rerank("q", CANDIDATES)

    assert len(scored) == len(CANDIDATES)
    assert set(_texts(scored)) == {"alpha", "bravo", "charlie", "delta"}
    assert _texts(scored)[:2] == ["bravo", "alpha"]


def test_ignores_junk_out_of_range_and_duplicate_numbers() -> None:
    scored = _reranker_replying("ranking: 99, 2, 2, 3").rerank("q", CANDIDATES)

    assert _texts(scored)[:2] == ["bravo", "charlie"]   # 99 dropped, duplicate 2 ignored
    assert len(scored) == len(CANDIDATES)


def test_a_stray_minus_sign_is_read_as_its_digits() -> None:
    """Documents a deliberate looseness: the parser scans for digit runs, so
    "-1" contributes 1. Being tolerant of malformed replies is worth more here
    than being strict — the alternative is discarding a usable ranking."""
    scored = _reranker_replying("2, -1").rerank("q", CANDIDATES)

    assert _texts(scored)[:2] == ["bravo", "alpha"]


def test_unparseable_reply_keeps_fusion_order() -> None:
    scored = _reranker_replying("I could not rank these.").rerank("q", CANDIDATES)

    assert _texts(scored) == ["alpha", "bravo", "charlie", "delta"]


def test_provider_failure_fails_open_to_fusion_order() -> None:
    """A reranker outage degrades ranking; it must not take retrieval down."""
    chat = MagicMock()
    chat.invoke.side_effect = RuntimeError("provider down")

    scored = LlmReranker(chat_model=chat).rerank("q", CANDIDATES)

    assert _texts(scored) == ["alpha", "bravo", "charlie", "delta"]


def test_single_candidate_skips_the_model_call() -> None:
    chat = MagicMock()
    scored = LlmReranker(chat_model=chat).rerank("q", _docs("only"))

    assert _texts(scored) == ["only"]
    chat.invoke.assert_not_called()


def test_empty_candidates_return_empty() -> None:
    assert LlmReranker(chat_model=MagicMock()).rerank("q", []) == []
