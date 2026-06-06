-- 001_extensions.sql
-- Required Postgres extensions.

-- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Vector similarity search (design §10). If you use an external vector DB
-- instead of pgvector, this is optional and source_chunks.embedding_id /
-- the external store hold the vectors.
CREATE EXTENSION IF NOT EXISTS vector;
