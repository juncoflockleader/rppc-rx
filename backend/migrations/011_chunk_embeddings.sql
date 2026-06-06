-- 011_chunk_embeddings.sql  (design §10)
-- Store chunk embeddings in-DB with pgvector. The column is unsized `vector`
-- so it accepts whatever dimension the configured embedding provider emits
-- (fake=64, openai text-embedding-3-small=1536). MVP uses brute-force cosine
-- search (sequential scan) — fine at the §22.1 scale. Add an HNSW/IVFFlat index
-- with a fixed dimension once a single production embedding model is chosen.

ALTER TABLE source_chunks ADD COLUMN IF NOT EXISTS embedding vector;
