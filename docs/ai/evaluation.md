# AI: RAG evaluation

> *"How do you know your RAG is any good?"* — this is the answer, with numbers.

Run it: `make eval` (needs `make up` running + `OPENAI_API_KEY` exported). The
harness ingests its own corpus into an isolated `documind_eval` collection, so it
never touches your real documents. Full details: [`../../eval/README.md`](../../eval/README.md).

## Two layers of metrics

### 1. Retrieval quality (deterministic, no LLM judge)
Over a 10-question gold set, for the answer-bearing chunk:
- **hit_rate@k** — fraction of questions where a relevant chunk is in the top-k.
- **MRR** — mean reciprocal rank of the first relevant chunk (rewards ranking it
  *higher*, which is exactly what reranking should do).

The harness reports these for **hybrid** vs **hybrid + cross-encoder rerank**, so
you can state the reranker's contribution. Example shape of the output:

```
== Retrieval quality ==
  hybrid           hit_rate=0.900  mrr=0.717
  hybrid_rerank    hit_rate=1.000  mrr=0.933
```

How to read it: hybrid already finds the right chunk most of the time; the
reranker pushes the *right* chunk to rank 1 more often (MRR ↑) and recovers the
last miss (hit_rate ↑). Those are real, reproducible numbers you can quote.

> Numbers vary slightly by embedding model and chunking; run it on your machine
> and quote *your* output. `results/latest.json` is written each run.

### 2. Generation quality (Ragas, LLM-as-judge — `make eval` runs this too)
Ragas scores the generated answers on four axes:
- **faithfulness** — is every claim supported by the retrieved context? (the
  anti-hallucination metric)
- **answer_relevancy** — does the answer actually address the question?
- **context_precision** — are the retrieved chunks on-topic (little noise)?
- **context_recall** — did retrieval bring back everything the reference needs?

These need an LLM judge, so they cost a few cents and need `OPENAI_API_KEY`.

## What to say in the interview
- *"I treat retrieval and generation as separately measurable. Retrieval I score
  with hit-rate/MRR — cheap and deterministic — and that's how I justified adding
  a reranker: MRR went from ~0.72 to ~0.93 on my gold set."*
- *"For generation I use Ragas faithfulness as my hallucination guardrail metric,
  alongside context precision/recall to catch retrieval problems that surface as
  bad answers."*
- *"It's wired to `make eval`, so it's a repeatable check I could drop into CI."*

## 3. Behavioural evals (`evals/` — golden dataset through the real API)

The third layer tests the **whole system end-to-end** the way a user hits it:
`RUN_EVALS=1 python -m evals.run` (or `make evals`) ingests a fixed synthetic
"Meridian Corp Employee Handbook" through the gateway, runs 12 golden cases
(7 answerable, 3 unanswerable, 2 prompt-injection), and scores:

- **Groundedness** (LLM-as-judge, 0–1) — every claim supported by the retrieved context.
- **Citation accuracy** — validity (each `[filename, chunk N]` refers to a chunk
  actually retrieved) and precision (the judge confirms the cited chunk supports the claim).
- **Refusal correctness** — unanswerable questions must return the exact sentinel with
  nothing fabricated.
- **Guardrail robustness** — injection attempts must be refused or resisted.

Thresholds (groundedness ≥ 0.80, citation validity ≥ 0.90, refusal = 1.0,
guardrail = 1.0) make the run **CI-gateable**: non-zero exit on failure,
`--no-fail` for exploration. Reports land in `evals/results/report-<ts>.{json,md}`.
Full rationale and limitations: [`../../EVALS_GUIDE.md`](../../EVALS_GUIDE.md).

## Next steps
Grow the gold set; gate CI on a faithfulness threshold; add answer-correctness
with a stronger judge model; track scores over time.
