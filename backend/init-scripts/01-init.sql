-- Runs once on the first start of the postgres container.
--
-- We only need to guarantee the pgvector extension exists. The chunk/embedding
-- tables are created and managed by LangChain's PGVector integration
-- (langchain_pg_collection + langchain_pg_embedding), and the `documents`
-- metadata table is created by SQLAlchemy at app startup. Keeping this script
-- tiny avoids drift between hand-written DDL and what the libraries expect.

CREATE EXTENSION IF NOT EXISTS vector;

-- NOTE ON THE ANN INDEX:
-- LangChain's PGVector does NOT create an approximate-nearest-neighbour index
-- by default. It stores vectors in langchain_pg_embedding and similarity search
-- runs as an EXACT sequential scan — correct and fast enough at small/medium
-- scale, which is what this project relies on. At large scale you would add an
-- index on that table. Prefer HNSW: it builds incrementally and handles rows
-- inserted after the index is created, whereas IVFFlat trains its clusters on
-- the data present at build time (so you must REINDEX after a bulk load):
--     CREATE INDEX ON langchain_pg_embedding USING hnsw (embedding vector_cosine_ops);
