# `eval/` — RAG evaluation harness

Answers the interview question *"how do you know your RAG is any good?"* with
numbers you can reproduce.

## What it measures
- **Retrieval** (no LLM judge, always runs): `hit_rate@k` and `MRR` over a gold
  Q&A set — comparing **hybrid retrieval** with vs without the **cross-encoder
  reranker**. This is the before/after that justifies reranking.
- **Generation** (`--judge`, uses Ragas + an LLM judge): `faithfulness`,
  `answer_relevancy`, `context_precision`, `context_recall`.

## Layout
- `corpus/` — a small sample document set (the Acme handbook).
- `gold/qa.jsonl` — 10 question / relevant-substring / ground-truth triples.
- `run_eval.py` — ingests the corpus into an isolated collection, then scores.
- `results/latest.json` — written on each run.

## Run it
```bash
# from the repo root, with the stack's Postgres up (make up) and OPENAI_API_KEY set
pip install -e libs/documind_contracts -e libs/documind_common
pip install -r eval/requirements.txt
make eval                 # retrieval + generation metrics on the documind_eval collection
```

`make eval` sets `VECTOR_COLLECTION=documind_eval` so the harness never touches
your real documents. Needs `OPENAI_API_KEY` (embeddings) and Postgres reachable.

See [`../docs/ai/evaluation.md`](../docs/ai/evaluation.md) for how to read the
numbers and what to say about them.
