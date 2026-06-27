-- Runs once on the first start of the postgres container.
--
-- We only need to guarantee the pgvector extension exists. The chunk/embedding
-- tables are created by LangChain's PGVector integration (langchain_pg_collection
-- + langchain_pg_embedding); the `documents` table is created by document-service
-- and the `users` table by the gateway at startup. Keeping this script tiny
-- avoids drift between hand-written DDL and what the services/libraries expect.

CREATE EXTENSION IF NOT EXISTS vector;

-- NOTE ON THE ANN INDEX:
-- LangChain's PGVector does NOT create an approximate-nearest-neighbour index by
-- default; similarity search runs as an exact scan — correct and fast enough at
-- small/medium scale. At large scale add an HNSW index (builds incrementally and
-- handles rows inserted after creation, unlike IVFFlat which needs a REINDEX):
--     CREATE INDEX ON langchain_pg_embedding USING hnsw (embedding vector_cosine_ops);
