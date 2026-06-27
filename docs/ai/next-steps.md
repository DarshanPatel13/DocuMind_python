# AI: deliberately deferred (talk about these)

Scoped out of the 3-day build on purpose — knowing *why* and *how* you'd add them
is the point. Each is a strong follow-up answer.

| Idea | What it adds | Why deferred / how I'd do it |
|---|---|---|
| **Agentic tool-calling (LangGraph)** | LLM chooses tools (`search`, `summarize`, `compare_documents`), multi-step reasoning | Big surface area; I'd model it as a LangGraph state machine with a ReAct loop and the existing retriever as one tool |
| **MCP server** | Expose the document search over the Model Context Protocol so any MCP client can use the corpus | Add an MCP server wrapping `documind_common.retrieval.retrieve` |
| **Semantic caching** | Cache answers for semantically-similar questions (embed the question, match in Redis) → big latency/cost win | Add a Redis vector cache keyed by question embedding, with a similarity threshold |
| **Model router** | Cheap model for easy questions, strong model for hard ones; fallback chain | Classify question difficulty (length/heuristic/LLM), route accordingly; wrap providers with a fallback |
| **Cross-encoder by default** | Best retrieval precision in the running service | Ships off by default to keep the image torch-free; flip `RERANKER=cross-encoder`, or use Cohere rerank to avoid local torch |
| **Indirect-injection defence** | Handle malicious instructions hidden *inside* uploaded PDFs | Sanitize/quarantine extracted text; treat document content as untrusted in the prompt |
| **Eval in CI** | Gate merges on a faithfulness/MRR threshold | Run `eval/run_eval.py` in GitHub Actions against a fixed corpus |

These sit on top of what's already built: hybrid retrieval + reranking
([rag-architecture](rag-architecture.md)), evaluation ([evaluation](evaluation.md)),
observability ([observability](observability.md)), and guardrails ([guardrails](guardrails.md)).
