-- 012_persona_canon.sql  (design §10 persona_canon index)
-- Chunked + embedded persona canonical corpus. Kept separate from
-- source_chunks so retrieval can target one space at a time (§4.4): a line's
-- evidence is either project source material or persona canon, never ambiguous.

CREATE TABLE persona_canon_chunks (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    persona_version_id    UUID NOT NULL REFERENCES persona_versions(id) ON DELETE CASCADE,
    persona_corpus_doc_id UUID NOT NULL REFERENCES persona_corpus_docs(id) ON DELETE CASCADE,
    chunk_index           INT NOT NULL,
    text                  TEXT NOT NULL,
    token_count           INT,
    concepts              JSONB,          -- doc-level concept tags (§10.3)
    embedding             vector,         -- unsized; see 011 note
    embedding_id          TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_persona_canon_chunks_version ON persona_canon_chunks(persona_version_id);
CREATE INDEX idx_persona_canon_chunks_doc ON persona_canon_chunks(persona_corpus_doc_id);
