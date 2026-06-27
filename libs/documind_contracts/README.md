# `documind_contracts` — shared wire contracts

Pydantic models for everything that crosses a service boundary:

- **Events** (`events.py`) — the Kafka `document.uploaded` payload.
- **DTOs** (`schemas.py`) — HTTP request/response bodies (`AskRequest`, `DocumentResponse`, …).
- **Status** (`status.py`) — the `DocumentStatus` lifecycle enum.

## Why a shared library instead of copy-paste?

This is a deliberate trade-off, and a common interview question.

| | Shared library (what we chose) | Duplicate the models in each service |
|---|---|---|
| Drift | Impossible — one definition | Easy: producer adds a field, consumer never sees it |
| Coupling | Services share a dependency; bumping it rebuilds both | Fully independent deploys |
| Best for | Contracts where agreement is **mandatory** (events, DTOs) | Internal models a service owns alone |

**Rule we apply:** if two services *must* agree on a shape for the system to work
(a Kafka event, an HTTP DTO), it goes here. Anything a single service owns
internally (e.g. its ORM rows, its domain errors) stays in that service.

**Java analogy:** this is the classic shared `*-api` / `*-contracts` Maven module
that both a producer and a `@KafkaListener` consumer depend on — same reasoning,
same trade-off.

> Next step (out of scope for the 3-day build): generate these from a single
> source — e.g. JSON Schema or Protobuf — so the **TypeScript** frontend types are
> generated from the same contract instead of hand-mirrored in `src/types`.
