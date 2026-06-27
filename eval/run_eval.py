"""DocuMind RAG evaluation harness.

Two layers, run with `make eval` (or `python eval/run_eval.py`):

  1. RETRIEVAL metrics (always runs, no LLM judge) — hit-rate@k and MRR over a
     gold set, comparing hybrid retrieval WITH vs WITHOUT the cross-encoder
     reranker. This is the deterministic, cheap signal and the before/after
     story for reranking.

  2. GENERATION metrics (with --judge) — Ragas faithfulness, answer relevancy,
     context precision, and context recall. Uses an LLM-as-judge, so it needs
     OPENAI_API_KEY and costs a few cents.

Both need Postgres (for the vector store) and OPENAI_API_KEY (for embeddings).
The harness ingests its own corpus into an isolated collection so it never
touches your real documents — set VECTOR_COLLECTION=documind_eval (the Make
target does this for you).

Usage:
    python eval/run_eval.py                 # retrieval metrics only
    python eval/run_eval.py --judge         # + Ragas generation metrics
    python eval/run_eval.py --k 4 --candidates 20
"""
from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter

from documind_common import vector_store
from documind_common.config import settings
from documind_common.providers import get_chat_model
from documind_common.reranker import CrossEncoderReranker
from documind_common.retrieval import retrieve

ROOT = Path(__file__).parent
CORPUS_DIR = ROOT / "corpus"
GOLD_FILE = ROOT / "gold" / "qa.jsonl"
RESULTS_FILE = ROOT / "results" / "latest.json"

SYSTEM_PROMPT = (
    "You are DocuMind. Answer ONLY from the provided context. "
    "If the context does not contain the answer, say you don't have enough information."
)


def load_gold() -> list[dict]:
    return [json.loads(line) for line in GOLD_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]


async def ingest_corpus() -> int:
    """Chunk + embed every file in corpus/ into the configured (eval) collection.
    Idempotent: deterministic ids upsert, so re-runs don't duplicate."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size_tokens * settings.chars_per_token,
        chunk_overlap=settings.overlap_tokens * settings.chars_per_token,
        length_function=len,
    )
    total = 0
    for path in sorted(CORPUS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        chunks = [c for c in splitter.split_text(text) if c.strip()]
        doc_id = uuid.uuid5(uuid.NAMESPACE_URL, path.name)
        total += await vector_store.add_chunks(doc_id, path.name, chunks)
    return total


def _hit_and_rank(docs, relevant_substring: str) -> tuple[bool, float]:
    needle = relevant_substring.lower()
    for rank, doc in enumerate(docs, start=1):
        if needle in doc.page_content.lower():
            return True, 1.0 / rank
    return False, 0.0


async def retrieval_metrics(gold: list[dict], k: int, candidates: int) -> dict:
    """Compute hit@k and MRR for hybrid-only vs hybrid+rerank."""
    reranker = None
    try:
        reranker = CrossEncoderReranker(settings.reranker_model)
    except Exception as exc:  # noqa: BLE001
        print(f"  (reranker unavailable: {exc}; install sentence-transformers to compare)")

    base_hits = base_mrr = rr_hits = rr_mrr = 0.0
    for item in gold:
        q, sub = item["question"], item["relevant_substring"]
        fused = await retrieve(q, candidates, use_reranker=False)
        fused_docs = [d for d, _ in fused]

        hit, mrr = _hit_and_rank(fused_docs[:k], sub)
        base_hits += hit
        base_mrr += mrr

        if reranker is not None:
            reranked = [d for d, _ in reranker.rerank(q, fused_docs)][:k]
            hit, mrr = _hit_and_rank(reranked, sub)
            rr_hits += hit
            rr_mrr += mrr

    n = len(gold)
    out = {
        "hybrid": {"hit_rate": base_hits / n, "mrr": base_mrr / n},
    }
    if reranker is not None:
        out["hybrid_rerank"] = {"hit_rate": rr_hits / n, "mrr": rr_mrr / n}
    return out


async def generation_metrics(gold: list[dict], k: int) -> dict | None:
    """Ragas generation metrics (LLM judge). Best-effort: skips with a message
    if ragas isn't installed or the run fails."""
    try:
        from ragas import EvaluationDataset, evaluate
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )

        from documind_common.providers import get_embeddings
    except ImportError:
        print("  (ragas not installed; `pip install -r eval/requirements.txt` to enable --judge)")
        return None

    chat = get_chat_model()
    samples = []
    for item in gold:
        q = item["question"]
        results = await retrieve(q, k)
        contexts = [d.page_content for d, _ in results]
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Context:\n{chr(10).join(contexts)}\n\nQuestion: {q}"),
        ]
        answer = (await chat.ainvoke(messages)).content
        samples.append(
            {
                "user_input": q,
                "response": answer if isinstance(answer, str) else str(answer),
                "retrieved_contexts": contexts,
                "reference": item["ground_truth"],
            }
        )

    dataset = EvaluationDataset.from_list(samples)
    try:
        result = evaluate(
            dataset=dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            llm=LangchainLLMWrapper(chat),
            embeddings=LangchainEmbeddingsWrapper(get_embeddings()),
        )
        return {k: float(v) for k, v in result._repr_dict.items()} if hasattr(result, "_repr_dict") else dict(result)
    except Exception as exc:  # noqa: BLE001
        print(f"  (ragas run failed: {exc})")
        return None


def _fmt(metrics: dict) -> str:
    return "  ".join(f"{k}={v:.3f}" for k, v in metrics.items())


async def main() -> None:
    parser = argparse.ArgumentParser(description="DocuMind RAG eval")
    parser.add_argument("--k", type=int, default=settings.top_k)
    parser.add_argument("--candidates", type=int, default=settings.retrieval_candidates)
    parser.add_argument("--judge", action="store_true", help="also run Ragas generation metrics")
    args = parser.parse_args()

    print(f"Collection: {settings.vector_collection}  |  k={args.k}  candidates={args.candidates}")
    gold = load_gold()
    print("Ingesting corpus … ", end="", flush=True)
    n_chunks = await ingest_corpus()
    print(f"{n_chunks} chunks indexed, {len(gold)} gold questions\n")

    print("== Retrieval quality ==")
    retr = await retrieval_metrics(gold, args.k, args.candidates)
    for name, m in retr.items():
        print(f"  {name:16s} {_fmt(m)}")

    gen = None
    if args.judge:
        print("\n== Generation quality (Ragas) ==")
        gen = await generation_metrics(gold, args.k)
        if gen:
            print(f"  {_fmt(gen)}")

    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(json.dumps({"retrieval": retr, "generation": gen}, indent=2), encoding="utf-8")
    print(f"\nSaved → {RESULTS_FILE.relative_to(ROOT.parent)}")


if __name__ == "__main__":
    asyncio.run(main())
