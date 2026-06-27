# document-service

Owns the **write side** of DocuMind: uploads, document metadata, and the
asynchronous ingestion pipeline.

## Responsibility
- Accept PDF uploads (validate the `%PDF` magic bytes + size), store the file,
  insert a `documents` row (`UPLOADED`), and publish `document.uploaded` to Kafka.
- Run the **ingestion consumer** (in-process background task): extract → chunk →
  embed → upsert into pgvector → mark the row `READY`. Retries 3× with backoff;
  on final failure marks `FAILED` and parks the event on the DLT.

## API (behind the gateway)
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/documents` | upload a PDF → `202 {document_id}` |
| `GET` | `/api/documents` | list documents + status |
| `GET` | `/health` | liveness |
| `GET` | `/ready` | readiness (metadata DB reachable) |

## Events
- **Produces:** `document-events` (`DocumentUploadedEvent`), `document-events.DLT`.
- **Consumes:** `document-events` (its own ingestion consumer).

## Data owned
- Postgres `documents` table (metadata) — private to this service.
- Writes chunk vectors into the **shared** pgvector store (see `docs/adr/0001`).

## Run / test
```bash
# locally (needs infra from `docker compose up postgres kafka`)
pip install -e ../../libs/documind_contracts -e ../../libs/documind_common
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
pytest
```

## Java analogy
A Spring Boot service with a `@RestController` for uploads, a `@KafkaListener`
for ingestion, and Spring Data JPA for the `documents` table — here it's FastAPI
+ aiokafka + SQLAlchemy async.
