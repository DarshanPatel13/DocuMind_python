# AI: RAG architecture (retrieval + generation)

## The pipeline

```
question
  │
  ├─ guardrail: prompt-injection screen ──► refuse if flagged
  │
  ├─ RETRIEVAL (documind_common/retrieval.py)
  │     ├─ vector arm    : pgvector cosine (semantic recall)
  │     ├─ keyword arm   : Postgres full-text search (exact terms/IDs)
  │     ├─ fuse          : Reciprocal Rank Fusion (RRF)
  │     └─ rerank        : cross-encoder re-scores top-N → top-k   (optional)
  │
  ├─ GROUNDED PROMPT (query-service/app/prompt.py)
  │     └─ "answer ONLY from context; cite [filename, chunk N]; else say you don't know"
  │
  └─ GENERATION: stream tokens (SSE)  + persist turn
        └─ traced in Langfuse when configured
```

## Why each piece

**Hybrid retrieval.** Dense vectors match *meaning* but miss rare exact tokens
(codes, names, acronyms); keyword/full-text matches *exact terms* but misses
paraphrases. Running both and fusing wins consistently. We use Postgres'
built-in full-text search on the same table pgvector already stores the chunk
text in — so no extra datastore.

**Reciprocal Rank Fusion (RRF).** `score = Σ 1/(k + rank)` across the two arms.
It fuses by *rank*, not raw score, so we don't have to calibrate cosine distance
against `ts_rank`. A chunk that ranks well in *either* arm surfaces; ranking in
*both* compounds.

**Cross-encoder reranking.** First-stage retrieval uses a bi-encoder (query and
chunk embedded separately) — fast, but it never sees the pair together. A
cross-encoder scores `(query, chunk)` jointly: much more accurate, too slow for
the whole corpus, perfect for re-scoring the top ~20. Default `RERANKER=none`
keeps the image torch-free; set `RERANKER=cross-encoder` to enable it (or use
Cohere's rerank API in production to avoid local torch).

**Grounding guard.** If retrieval returns nothing, we return a fixed sentinel and
never call the LLM — it literally cannot hallucinate from empty context.

## How we prove it's good
See [`evaluation.md`](evaluation.md) — `make eval` reports hit-rate@k and MRR with
vs without reranking, plus Ragas faithfulness/relevancy/precision/recall.

## Java analogy
Composing two Spring Data queries (vector + full-text), merging their result
pages with a fusion ranker, then applying a scoring `Comparator` (the reranker)
before handing the top-k to the prompt builder.

## Performance note (next step)
The keyword arm computes `to_tsvector(...)` on the fly. At scale, add a stored
`tsvector` column + GIN index on `langchain_pg_embedding`, and an HNSW index for
the vector arm (see `infra/init-scripts/01-init.sql`).
