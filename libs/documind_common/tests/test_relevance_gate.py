"""The relevance gate — the difference between "the search returned rows" and
"the search found something about the question".

These cases exist because every stage after the vector search hides that
distinction: `LIMIT k` always yields k rows, RRF replaces distances with
rank-only scores, and a reranker only reorders. If the gate regresses, the
system stops refusing and starts guessing, silently.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from langchain_core.documents import Document

from documind_common import retrieval
from documind_common.config import settings

THRESHOLD = 0.55


@pytest.fixture(autouse=True)
def _gate_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "max_distance", THRESHOLD)
    monkeypatch.setattr(settings, "hybrid_enabled", True)
    monkeypatch.setattr(settings, "reranker", "none")


def _doc(text: str, idx: int = 0) -> Document:
    return Document(
        page_content=text,
        metadata={"filename": "policy.pdf", "chunk_index": idx, "chunk_id": f"c{idx}"},
    )


def _arms(monkeypatch: pytest.MonkeyPatch, vector_pairs, keyword_docs):
    monkeypatch.setattr(
        retrieval, "_vector_candidates_scored", AsyncMock(return_value=vector_pairs)
    )
    monkeypatch.setattr(retrieval, "_keyword_candidates", AsyncMock(return_value=keyword_docs))


async def test_far_vector_hits_with_no_keyword_match_are_not_relevant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The original bug, pinned. A full top-k comes back for a question the
    corpus has never heard of; only the distances reveal it."""
    _arms(monkeypatch, [(_doc("Flood is excluded.", 1), 0.81), (_doc("Windstorm.", 2), 0.77)], [])

    result = await retrieval.retrieve_scored("What is our cyber liability limit?", 4)

    assert result.relevant is False
    assert result.best_vector_distance == pytest.approx(0.77)
    assert result.keyword_hits == 0
    # Chunks still come back — refusing is the caller's job, and the scores are
    # what make that decision auditable.
    assert result.docs


async def test_a_close_vector_hit_is_relevant(monkeypatch: pytest.MonkeyPatch) -> None:
    _arms(monkeypatch, [(_doc("The standard deductible is $25,000.", 1), 0.19)], [])

    result = await retrieval.retrieve_scored("What is the standard deductible?", 4)

    assert result.relevant is True
    assert result.best_vector_distance == pytest.approx(0.19)


async def test_keyword_match_rescues_a_query_the_dense_arm_misses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The regression this design must avoid. Exact tokens — a code, an ID — are
    where embeddings are weakest and full-text search is strongest. Gating on
    distance alone would refuse exactly the queries the keyword arm exists for."""
    _arms(monkeypatch, [(_doc("unrelated boilerplate", 9), 0.88)], [_doc("Endorsement CP-04-31", 3)])

    result = await retrieval.retrieve_scored("CP-04-31", 4)

    assert result.relevant is True
    assert result.keyword_hits == 1


async def test_best_distance_comes_from_the_dense_arm_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keyword rows have no meaningful distance. If the gate ever measured them,
    every lexical hit would read as a perfect match and nothing would be refused."""
    _arms(monkeypatch, [(_doc("far away", 1), 0.93)], [_doc("lexical hit", 2)])

    result = await retrieval.retrieve_scored("something", 4)

    assert result.best_vector_distance == pytest.approx(0.93)


async def test_empty_corpus_is_not_relevant(monkeypatch: pytest.MonkeyPatch) -> None:
    _arms(monkeypatch, [], [])

    result = await retrieval.retrieve_scored("anything", 4)

    assert result.relevant is False
    assert result.docs == []
    assert result.best_vector_distance is None


async def test_zero_threshold_disables_the_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "max_distance", 0)
    _arms(monkeypatch, [(_doc("nowhere near", 1), 0.97)], [])

    result = await retrieval.retrieve_scored("cyber liability limit", 4)

    assert result.relevant is True


async def test_vector_only_mode_still_gates_on_distance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "hybrid_enabled", False)
    keyword = AsyncMock(return_value=[])
    monkeypatch.setattr(
        retrieval, "_vector_candidates_scored", AsyncMock(return_value=[(_doc("far", 1), 0.90)])
    )
    monkeypatch.setattr(retrieval, "_keyword_candidates", keyword)

    result = await retrieval.retrieve_scored("unanswerable", 4)

    assert result.relevant is False
    keyword.assert_not_awaited()            # the keyword arm must not run when hybrid is off


async def test_scoped_whole_document_reads_bypass_the_gate() -> None:
    result = retrieval.RetrievalResult.scoped([_doc("page one", 0)])

    assert result.relevant is True
    assert result.best_vector_distance is None


async def test_retrieve_delegates_to_retrieve_scored(monkeypatch: pytest.MonkeyPatch) -> None:
    """One implementation, two entrypoints — they must not drift."""
    _arms(monkeypatch, [(_doc("hit", 1), 0.2)], [])

    pairs = await retrieval.retrieve("q", 4)

    assert [d.page_content for d, _ in pairs] == ["hit"]
