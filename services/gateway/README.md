# gateway

The single public entry point. The browser talks **only** to the gateway; the
internal services are never exposed directly.

## Responsibility (all the cross-cutting concerns)
- **JWT auth** — `POST /auth/login` checks a bcrypt-hashed password in the `users`
  table and issues a signed token; every `/api/*` route validates it.
- **CORS** — allows the frontend origin.
- **Rate limiting** — Redis-backed fixed window on the expensive `POST /api/ask`.
- **Routing + streaming** — reverse-proxies to document-service / query-service,
  **passing SSE through unbuffered** so token streaming survives the hop.

## Routes
| Method | Path | Auth | Routed to |
|---|---|---|---|
| `POST` | `/auth/login` | public | (gateway) → JWT |
| `GET/POST` | `/api/documents` | JWT | document-service |
| `POST` | `/api/ask` | JWT + rate-limit | query-service |
| `GET` | `/api/conversations/{id}` | JWT | query-service |
| `GET` | `/health`, `/ready` | public | (gateway) |

## Demo login
`demo` / `demo12345` (seeded on startup; override via `DEMO_USERNAME` /
`DEMO_PASSWORD`).

## Run / test
```bash
pip install -e ../../libs/documind_contracts -e ../../libs/documind_common
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
pytest
```

## Why a custom FastAPI gateway (not Traefik/Nginx) for Day 1?
A thin FastAPI gateway lets us show the auth + rate-limit + SSE-passthrough logic
*in code we can read and explain*. In production you'd often put Traefik or an
API gateway in front; that's listed as a next step in `docs/adr/0001`.

**Java analogy:** Spring Cloud Gateway with a JWT auth filter and a Redis
rate-limiter filter.
