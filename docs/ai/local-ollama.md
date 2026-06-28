# Run DocuMind for free / offline (Ollama)

DocuMind's LLM layer is provider-pluggable. Besides OpenAI and Anthropic, it can
run **fully local and free** with [Ollama](https://ollama.com) in Docker — no API
key, no network. This swaps **both** the chat model and the embeddings.

## One-time setup
```bash
make ollama-up      # starts the Ollama container + pulls llama3.2:3b + nomic-embed-text
```
Then enable the local block in `.env` (it's commented in `.env.example`):
```env
LLM_PROVIDER=ollama
CHAT_MODEL=llama3.2:3b
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSIONS=768
VECTOR_COLLECTION=documind_ollama
OLLAMA_BASE_URL=http://ollama:11434
```
Restart the services that talk to the LLM:
```bash
docker compose up -d --no-deps document-service query-service
```
Re-upload a PDF (so it's embedded with the local model) and ask away — `$0`.

## Why `VECTOR_COLLECTION=documind_ollama` (the important gotcha)
A pgvector collection has a **fixed dimension**. OpenAI `text-embedding-3-small`
is 1536-d; `nomic-embed-text` is 768-d. You cannot mix them in one collection, so
the local setup uses its **own collection**. Switching back to OpenAI just means
switching the collection back (your OpenAI vectors are still there). If you ever
need to wipe vectors entirely: `docker compose down -v`.

## How it works (one config branch, no app changes)
`libs/documind_common/documind_common/providers.py`:
- `get_chat_model()` → `ChatOllama(model=…, base_url=OLLAMA_BASE_URL)`
- `get_embeddings()` → `OllamaEmbeddings(model=…, base_url=OLLAMA_BASE_URL)`

Everything downstream — hybrid retrieval, the grounded prompt, SSE streaming,
guardrails, Langfuse tracing, the Ragas eval — is identical. That's the whole
point of the provider seam (Spring analogy: swapping a `@Qualifier` bean).

## Honest trade-offs
| | OpenAI (default) | Ollama (local) |
|---|---|---|
| Cost | ~cents | **free** |
| Network | required | **offline** |
| Answer quality | high (`gpt-4o-mini`) | lower (small local model) |
| Speed | fast | slow on CPU; good on GPU |
| Resources | none | ~3–5 GB download, ~8 GB RAM for 7B |
| Ragas judge | reliable | weaker/noisier (local judge) |

**Recommendation:** use OpenAI for the polished demo and quoting eval numbers; use
Ollama to prove the system is provider-agnostic and to develop offline. Want a
bigger/better local model? Try `CHAT_MODEL=qwen2.5:7b` (needs more RAM).

## Interview soundbite
*"It's provider-pluggable — OpenAI, Anthropic, or fully local via Ollama, switched
by one env var with zero code change. Embeddings and chat both swap; the only
real constraint is that vector dimension is part of the storage contract, so each
provider gets its own collection. Observability and evaluation are provider-agnostic."*
