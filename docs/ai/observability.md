# AI: LLM observability (Langfuse)

> *"How would you debug a bad answer in production?"* — open the trace.

A black-box LLM call is unobservable: you can't see the exact prompt sent, the
tokens used, the cost, or the latency. **Langfuse** captures all of that per call.

## How it's wired
- `query-service/app/observability.py` builds a Langfuse **LangChain callback
  handler**. LangChain emits lifecycle events for every run; the handler records
  them — so we get traces *without changing the ask logic*. We just pass the
  handler in the call's `config={"callbacks": [...]}` (see `ask_service.py`).
- It's a **no-op unless `LANGFUSE_PUBLIC_KEY` is set**, so the default stack runs
  with zero observability overhead. You opt in.

## Run it
```bash
make observability          # starts Langfuse at http://localhost:3000
# 1. open http://localhost:3000, create an account + a project
# 2. copy the project's public/secret keys into .env:
#      LANGFUSE_PUBLIC_KEY=pk-lf-...
#      LANGFUSE_SECRET_KEY=sk-lf-...
#      LANGFUSE_HOST=http://langfuse:3000
# 3. restart query-service:  docker compose up -d query-service
# 4. ask a question in the UI, then watch the trace appear in Langfuse
```
(Cloud alternative: use Langfuse Cloud's free tier and set `LANGFUSE_HOST=https://cloud.langfuse.com` — no self-hosting.)

## What a trace shows
For each `/api/ask`: the rendered prompt (system + grounded context), the model
and parameters, input/output **token counts**, **estimated cost**, and
**latency**. Over time: cost per day, p95 latency, and which prompts are slow or
expensive.

> Add a screenshot of one trace here after your first run.

## What to say in the interview
*"Every LLM call is traced in Langfuse — prompt, tokens, cost, latency. When an
answer looks wrong, I open its trace and see the exact context the model was
given, which usually tells me whether it was a retrieval problem or a generation
problem. It's behind a feature flag (the public key), so it's free when off."*

## Next step
Link the Langfuse trace id to the request's correlation id / OpenTelemetry span
(Day 3) so one click jumps from an API trace to its LLM trace.

## Java analogy
A Micrometer/OpenTelemetry interceptor you register once — except specialized for
LLM calls (it understands prompts, tokens, and cost, not just HTTP timings).
