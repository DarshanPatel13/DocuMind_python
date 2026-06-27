"""Reciprocal Rank Fusion: ordering, score accumulation, and de-duplication."""
from __future__ import annotations

from langchain_core.documents import Document

from documind_common.retrieval import RRF_K, _doc_key, reciprocal_rank_fusion


def _doc(chunk_id: str, text: str = "x") -> Document:
    return Document(page_content=text, metadata={"chunk_id": chunk_id})


def test_doc_appearing_in_both_arms_outranks_single_arm() -> None:
    a, b, c = _doc("a"), _doc("b"), _doc("c")
    vector = [a, b]          # a is rank 0 here
    keyword = [c, a]         # a is rank 1 here -> a is in BOTH lists
    fused = reciprocal_rank_fusion([vector, keyword])
    order = [_doc_key(d) for d, _ in fused]
    assert order[0] == "a"   # rewarded for appearing in both arms


def test_scores_use_the_rrf_formula() -> None:
    a = _doc("a")
    # a is rank 0 in one list only -> 1 / (RRF_K + 0 + 1)
    fused = reciprocal_rank_fusion([[a]])
    (_, score), = fused
    assert score == 1.0 / (RRF_K + 1)


def test_dedupes_by_chunk_id() -> None:
    fused = reciprocal_rank_fusion([[_doc("a")], [_doc("a")]])
    assert len(fused) == 1            # same chunk_id collapses to one entry
    (_, score), = fused
    assert score == 2.0 / (RRF_K + 1)  # but its score is summed across both arms


def test_empty_input_is_empty() -> None:
    assert reciprocal_rank_fusion([[], []]) == []
