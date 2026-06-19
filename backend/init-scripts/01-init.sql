-- Runs once on the first start of the postgres container.
--
-- We only need to guarantee the pgvector extension exists. The chunk/embedding
-- tables are created and managed by LangChain's PGVector integration
-- (langchain_pg_collection + langchain_pg_embedding), and the `documents`
-- metadata table is created by SQLAlchemy at app startup. Keeping this script
-- tiny avoids drift between hand-written DDL and what the libraries expect.

CREATE EXTENSION IF NOT EXISTS vector;

-- NOTE ON THE ANN INDEX (IVFFlat vs HNSW):
-- PGVector creates an index on its embedding column. pgvector offers two
-- approximate-nearest-neighbour indexes:
--   * IVFFlat — k-means-clusters the vectors and probes only the nearest
--     clusters. Cheap to build, light on memory, great up to ~100k vectors,
--     but clusters reflect the data present at build time (REINDEX after a
--     big load).
--   * HNSW — a layered proximity graph: better recall/latency at large scale
--     and no build-time training, but slower builds and more memory.
-- Rule of thumb: IVFFlat until millions of vectors or measurable recall
-- problems, then switch to HNSW. The change is a one-line index swap.
