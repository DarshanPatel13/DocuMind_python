# Code Structure — where everything lives (and the Java/Spring equivalent)

> **Read this first if you come from Java/Spring.** It answers one question an
> interviewer will ask: *"how is your code organised?"* Short version: this
> project uses a **layered architecture**, exactly like a Spring Boot app — it
> just expresses each layer as a **Python module (a `.py` file)** instead of a
> **Java package (a folder of one-class files)**.

---

## "Does Python use service / repository / util packages like Java?"

**Yes — the layers are the same; the packaging convention is different.**

| | Java / Spring | Python (this repo) |
|---|---|---|
| Unit of code | one **public class per file** | a **module** = one `.py` file holding related functions/classes |
| A layer | a **package** (folder): `…/service/`, `…/repository/` | a **module**: `service.py`, `repository`-style module (`mongo.py`, `vector_store.py`) |
| When you split into folders | almost always (Java forces one class/file) | only when a module gets large; a flat module is **idiomatic and preferred** until then |
| Wiring | `@Component` + `@Autowired` (Spring container) | plain imports + a few module-level singletons built lazily |

So "I don't see a `service/` or `repository/` folder" is expected: in Python a
**file named `service.py` _is_ the service layer.** Deep package trees with one
function per file are considered over-engineering for services this size. This is
the same convention used by FastAPI's own docs and most production Python codebases.

> If an interviewer pushes on "where's your repository layer?", point at
> `vector_store.py` + `mongo.py` + `retrieval.py` (data access) and `models.py`
> (the entity) — that **is** the repository/persistence layer; it's just not in a
> folder called `repository/`.

---

## The layers, mapped to Spring

Every service follows the same shape:

```
HTTP request
   │
   ▼
routes*.py        ← Controller layer      (@RestController)
   │
   ▼
*_service.py      ← Service layer         (@Service)  — business logic, orchestration
   │
   ▼
data access       ← Repository layer      (@Repository / Spring Data)
   ├── models.py        entity            (@Entity)
   ├── db.py            datasource/session (DataSource + JPA/Hibernate config)
   ├── vector_store.py  pgvector access
   ├── retrieval.py     hybrid search queries
   └── mongo.py         Mongo access
   │
   ▼
messaging         ← producer.py / consumer.py   (KafkaTemplate / @KafkaListener)

cross-cutting (applied around the above):
   config.py       @ConfigurationProperties (typed env config)
   errors.py       exception types        (@ControllerAdvice handlers live in main.py)
   security.py / auth.py / rate_limit.py   Spring Security filter chain
   main.py         @SpringBootApplication + lifespan (startup/shutdown beans)
```

---

## File-by-file: what each one does

### `libs/` — shared modules (like internal Maven libraries imported by every service)

**`documind_contracts/`** — the shared API/event contract (DTOs). Like a
`*-api` / `*-dto` jar shared across microservices.
| File | Role |
|---|---|
| `schemas.py` | Pydantic request/response DTOs (`AskRequest`, `DocumentResponse`, `Citation`, …) — the JSON shapes crossing service boundaries. |
| `events.py` | Kafka event payloads (`DocumentUploadedEvent`). |
| `status.py` | `DocumentStatus` enum (UPLOADED → PROCESSING → READY/FAILED). |

**`documind_common/`** — shared infrastructure (config, AI providers, persistence,
logging). Like a `*-common` / `*-starter` jar.
| File | Role | Spring analogy |
|---|---|---|
| `config.py` | Typed settings + **provider profiles** (one `LLM_PROVIDER` switch derives model/embeddings/dimensions/collection). | `@ConfigurationProperties` |
| `providers.py` | `get_chat_model()` / `get_embeddings()` — the only place a concrete LLM class is named. | Spring AI `ChatModel`/`EmbeddingModel` beans |
| `vector_store.py` | pgvector read/write (the shared store). | a `@Repository` |
| `retrieval.py` | Hybrid retrieval: vector + keyword + RRF fusion + rerank. | a composed query service |
| `reranker.py` | Optional cross-encoder reranker (off by default, torch-free). | a strategy bean |
| `correlation.py` | ASGI middleware that puts an `X-Request-ID` on every request/log. | a servlet `Filter` + MDC |
| `logging.py` | structlog JSON logging config. | Logback config |

### `services/gateway/` — the only public service (auth, CORS, rate-limit, routing)
| File | Role | Spring analogy |
|---|---|---|
| `main.py` | App bootstrap, CORS, the `/api/*` reverse-proxy route. | `@SpringBootApplication` + Gateway routes |
| `proxy.py` | Streaming reverse proxy to internal services (keeps SSE token streaming alive). | Spring Cloud Gateway filter |
| `auth.py` | Login + `get_current_user` dependency (JWT verify). | Security service |
| `security.py` | JWT encode/verify + bcrypt password hashing. | `JwtEncoder` / `PasswordEncoder` |
| `rate_limit.py` | Redis fixed-window rate limiter on the expensive `/api/ask`. | a rate-limit filter |
| `config.py` | Gateway settings (JWT secret, upstream URLs, CORS). | `@ConfigurationProperties` |
| `db.py` | Users table session/engine + demo-user seeding. | DataSource + `CommandLineRunner` |

### `services/document-service/` — uploads + async ingestion
| File | Role | Spring analogy |
|---|---|---|
| `routes.py` | `POST /api/documents` (upload), `GET /api/documents` (list). | `@RestController` |
| `service.py` | Upload use-case: validate → store file → DB row → publish event. | `@Service` |
| `models.py` | `DocumentRow` SQLAlchemy entity (the `documents` table). | `@Entity` |
| `db.py` | Async SQLAlchemy engine/session + table creation. | JPA config |
| `producer.py` | Kafka producer (publishes `DocumentUploadedEvent`). | `KafkaTemplate` |
| `consumer.py` | `IngestionConsumer`: background Kafka listener, retries + DLT. | `@KafkaListener` + error handler |
| `ingestion.py` | The pipeline: extract → chunk → embed/store → mark READY (idempotent). | a `@Service` orchestrating the work |
| `pdf_extract.py` | PDF → text. | a util/helper bean |
| `chunking.py` | Split text into overlapping ~800-token chunks. | a util/helper bean |
| `errors.py` | Domain exceptions (`InvalidFileError`, `IngestionError`, …). | custom exceptions |

### `services/query-service/` — the RAG ask flow + conversation history
| File | Role | Spring analogy |
|---|---|---|
| `routes_ask.py` | `POST /api/ask` — streams the answer as Server-Sent Events. | `@RestController` (SSE) |
| `routes_conversations.py` | `GET /api/conversations/{id}` history. | `@RestController` |
| `ask_service.py` | `AskService`: guardrail → retrieve → build prompt → stream tokens → persist. | `@Service` |
| `intent.py` | Detects "list all / summarize" queries (drives whole-document mode). | a small strategy helper |
| `prompt.py` | Builds the grounded-only system+user messages. | prompt template |
| `guardrails.py` | Prompt-injection detection + refusal text. | an input-validation filter |
| `conversation_service.py` | Save/read conversation turns. | `@Service` over a repo |
| `mongo.py` | Motor (async Mongo) client + the `conversation_turns` collection. | `@Repository` |
| `observability.py` | Optional Langfuse tracing handler (no-op unless keys set). | a tracing aspect |
| `config.py` | Query-service settings (Mongo URI, top-k, …). | `@ConfigurationProperties` |

### Each service also has
- `main.py` — the FastAPI app + **lifespan** (startup/shutdown), where the DB,
  Kafka producer/consumer, and HTTP clients are started and stopped. This is the
  Spring application context lifecycle (`@PostConstruct` / `@PreDestroy` beans).
- `tests/` — pytest tests, mirroring the package (`test_chunking.py`,
  `test_security.py`, …). Like `src/test/java`.

---

## Why this is "production-shaped"

- **Separation of concerns** — routing, business logic, persistence, and messaging
  are each in their own module; no SQL inside a controller, no HTTP inside a model.
- **Shared contracts** — DTOs/events live in one shared library, so two services
  can never disagree on a payload shape (compile-time-ish safety via Pydantic).
- **Dependency inversion at the AI boundary** — callers depend on
  `get_chat_model()`, never on `ChatOpenAI`/`ChatOllama` directly, so the provider
  is a config switch (`LLM_PROVIDER`).
- **Idempotent, at-least-once messaging** — the consumer retries, dead-letters,
  and commits offsets only after success; ingestion skips already-READY docs.
- **Cross-cutting concerns centralized** — auth, CORS, rate-limiting, correlation
  IDs, and logging live at the edges (gateway + middleware), not sprinkled through
  business code.

See also: [`docs/HLD.md`](../HLD.md) (full design), [`docs/for-java-devs.md`](../for-java-devs.md) (concept-by-concept Java mapping).
