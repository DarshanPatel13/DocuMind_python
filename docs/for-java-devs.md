# DocuMind for Java / Spring developers

A translation layer. Everything in this project maps to something you already
know from Spring Boot — here's the dictionary, with the file to look at.

## Backend (Python ≈ Spring Boot)

| DocuMind (Python) | Spring / Java equivalent | Where |
|---|---|---|
| **FastAPI** app + `@router.post` | Spring Web `@RestController` / `@PostMapping` | `services/*/app/routes*.py` |
| **Pydantic** model | DTO + Bean Validation (`@Valid`, `@NotNull`) | `libs/documind_contracts` |
| **pydantic-settings** `Settings` | `@ConfigurationProperties` | `*/app/config.py` |
| **SQLAlchemy 2.0** ORM (async) | JPA / Hibernate entities + repositories | `document-service/app/models.py`, `db.py` |
| `async def` + `await` | reactive (`Mono`/`Flux`) or virtual threads | everywhere |
| **FastAPI dependency** (`Depends`) | constructor injection / `@Autowired` | `Depends(get_session)` |
| **aiokafka** producer / consumer | `KafkaTemplate` / `@KafkaListener` | `document-service/app/{producer,consumer}.py` |
| retries + **dead-letter topic** | `SeekToCurrentErrorHandler` + `DeadLetterPublishingRecoverer` | `consumer.py` |
| **Motor** (MongoDB) | Spring Data MongoDB | `query-service/app/mongo.py` |
| **structlog** + correlation id | SLF4J + MDC (`traceId`) / Sleuth | `libs/documind_common/{logging,correlation}.py` |
| **PyJWT** + **bcrypt** | Spring Security JWT filter + `BCryptPasswordEncoder` | `gateway/app/{security,auth}.py` |
| **Redis** rate limiter | Bucket4j + Redis | `gateway/app/rate_limit.py` |
| **httpx** streaming proxy | Spring Cloud Gateway / `WebClient` | `gateway/app/proxy.py` |
| **pytest** + monkeypatch | JUnit + Mockito | `*/tests/` |
| **uv/pip** + `requirements.txt` | Maven/Gradle + `pom.xml` | each service |
| **Dockerfile** per service | Spring Boot fat-jar + Dockerfile | `services/*/Dockerfile` |

## AI / RAG (the part Spring doesn't have a 1:1 for)

| DocuMind | Closest analogy |
|---|---|
| **LangChain** providers (`get_chat_model`) | Spring AI's `ChatModel` / `EmbeddingModel` interfaces |
| **provider profiles** (`LLM_PROVIDER` → models/dims/collection) | Spring **profiles** (`@Profile`) — pick a profile, get its config/beans |
| **Nginx** serving the SPA (no-cache HTML) | the servlet container / static resource handler + cache headers |
| **pgvector** similarity search | a custom JPA query, but over vectors |
| **hybrid retrieval + RRF** | merging two `Page<>` results with a fusion ranker |
| **cross-encoder reranker** | a scoring `Comparator` applied to candidates |
| **Ragas** eval | JUnit assertions, but on answer quality (LLM-as-judge) |
| **Langfuse** tracing | Micrometer/OpenTelemetry, specialized for LLM calls |
| **guardrails** | a request-validation `HandlerInterceptor` |

## Frontend (React ≈ a component MVC you control)

| DocuMind (React/TS) | Analogy |
|---|---|
| **TanStack Query** (`useDocuments`) | a caching repository layer for server state |
| **Zustand / Context** | a request/session-scoped bean for client state |
| **shadcn/ui + Radix** | a component library you *own the source of* (not a black-box JAR) |
| **Vite** | the build tool (think Maven for the frontend) |
| **Vitest / Playwright** | JUnit (unit) / Selenium (E2E) |
| **TypeScript** types mirroring Pydantic | shared DTOs between client and server |

## Three mental-model differences worth internalizing
1. **Async is explicit.** `async def` / `await` is everywhere instead of a thread
   pool you don't see. One process handles many requests by never blocking the
   event loop — slow/native calls are pushed to a thread with `asyncio.to_thread`.
2. **Config is the environment.** No XML/profiles; pydantic-settings reads env vars
   (typed) at startup. Compose injects them per service.
3. **Contracts are duck-typed but validated.** No compiler across service
   boundaries, so the *shared Pydantic models* in `documind_contracts` are how we
   keep producer and consumer honest — that's why they're a package, not copies.
