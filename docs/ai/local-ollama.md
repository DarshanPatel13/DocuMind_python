# Run DocuMind for free / offline (Ollama)

DocuMind's LLM layer is provider-pluggable. Besides OpenAI and Anthropic, it can
run **fully local and free** with [Ollama](https://ollama.com) in Docker — no API
key, no network. This swaps **both** the chat model and the embeddings.

## One-time setup
```bash
make ollama-up      # starts the Ollama container + pulls llama3.2:3b + nomic-embed-text
```
Then set **one line** in `.env`:
```env
LLM_PROVIDER=ollama
```
…and restart the services that talk to the LLM:
```bash
docker compose up -d document-service query-service
```
Re-upload a PDF (so it's embedded with the local model) and ask away — `$0`.

That single switch derives everything else: chat model `llama3.2:3b`, embeddings
`nomic-embed-text`, 768 dimensions, and a dedicated `documind_ollama` collection.
To go back to OpenAI, set `LLM_PROVIDER=openai` and restart — done.

## The dimension clash is handled for you
A pgvector collection has a **fixed dimension** (OpenAI `text-embedding-3-small`
is 1536-d; `nomic-embed-text` is 768-d), so you can't mix them. Each provider gets
its **own collection** automatically (`documind_openai` vs `documind_ollama`, see
`libs/documind_common/config.py`), so flipping back and forth never clashes and
never needs a re-index. To wipe all vectors entirely: `docker compose down -v`.

## How it works (one config branch, no app changes)
`libs/documind_common/documind_common/providers.py`:
- `get_chat_model()` → `ChatOllama(model=…, base_url=OLLAMA_BASE_URL)`
- `get_embeddings()` → `OllamaEmbeddings(model=…, base_url=OLLAMA_BASE_URL)`

Everything downstream — hybrid retrieval, the grounded prompt, SSE streaming,
guardrails, Langfuse tracing, the Ragas eval — is identical. That's the whole
point of the provider seam (Spring analogy: swapping a `@Qualifier` bean).

## Low on RAM? Use a smaller chat model
The default `llama3.2:3b` needs ~3–4 GB free; alongside Postgres/Kafka/Mongo it can
get OOM-killed (`llama-server … signal: killed`). Override with a lighter model in
`.env` and restart query-service:
```env
CHAT_MODEL=llama3.2:1b      # ~1.3 GB; verified end-to-end on a low-RAM box
```
```bash
docker compose up -d query-service
```
The override flows through because the services load `.env` (`env_file`), and the
profile only fills in what you leave blank.

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
