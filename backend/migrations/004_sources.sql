-- 004_sources.sql  (design §8.3 – §8.5)

-- sources -------------------------------------------------------------------
CREATE TABLE sources (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id         UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    type               TEXT NOT NULL,              -- text_paste | txt | md | pdf
    title              TEXT,
    original_filename  TEXT,
    object_storage_uri TEXT,
    parsed_text_uri    TEXT,
    status             TEXT NOT NULL DEFAULT 'uploaded',  -- uploaded|parsing|processed|failed
    metadata           JSONB,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sources_project_id ON sources(project_id);

-- source_chunks -------------------------------------------------------------
CREATE TABLE source_chunks (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id    UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    project_id   UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    chunk_index  INT NOT NULL,
    text         TEXT NOT NULL,
    token_count  INT,
    page_start   INT,
    page_end     INT,
    char_start   INT,
    char_end     INT,
    embedding_id TEXT,                              -- id in external vector store
    -- Optional: keep vectors in-DB instead of an external store.
    -- embedding vector(1536),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_id, chunk_index)
);

CREATE INDEX idx_source_chunks_source_id ON source_chunks(source_id);
CREATE INDEX idx_source_chunks_project_id ON source_chunks(project_id);

-- source_claims -------------------------------------------------------------
CREATE TABLE source_claims (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    claim_text      TEXT NOT NULL,
    -- argument | definition | example | evidence | quote | question | counterargument
    claim_type      TEXT,
    confidence      NUMERIC,
    source_chunk_id UUID REFERENCES source_chunks(id) ON DELETE SET NULL,
    page_number     INT,
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_source_claims_source_id ON source_claims(source_id);
CREATE INDEX idx_source_claims_project_id ON source_claims(project_id);
