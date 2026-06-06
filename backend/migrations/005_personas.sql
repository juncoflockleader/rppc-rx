-- 005_personas.sql  (design §8.6 – §8.8)
-- Persona assets are global library entities (not owned by a user/project).

-- persona_assets ------------------------------------------------------------
CREATE TABLE persona_assets (
    id          TEXT PRIMARY KEY,                  -- e.g. laozi, buddha, modern_host
    display_name TEXT NOT NULL,
    type        TEXT NOT NULL,                     -- historical_philosophical_persona | abstract_persona ...
    status      TEXT NOT NULL DEFAULT 'active',    -- active | beta | deprecated
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- persona_versions ----------------------------------------------------------
CREATE TABLE persona_versions (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    persona_id         TEXT NOT NULL REFERENCES persona_assets(id) ON DELETE CASCADE,
    version            TEXT NOT NULL,
    status             TEXT NOT NULL DEFAULT 'draft',  -- draft | beta | active | deprecated
    identity_profile   JSONB NOT NULL,
    knowledge_boundary JSONB NOT NULL,
    stance_matrix      JSONB NOT NULL,
    style_profile      JSONB NOT NULL,
    forbidden_moves    JSONB NOT NULL,
    voice_profile      JSONB NOT NULL,
    prompt_pack        JSONB NOT NULL,
    eval_summary       JSONB,
    release_notes      TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (persona_id, version)
);

CREATE INDEX idx_persona_versions_persona_id ON persona_versions(persona_id);

-- persona_corpus_docs -------------------------------------------------------
CREATE TABLE persona_corpus_docs (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    persona_version_id UUID NOT NULL REFERENCES persona_versions(id) ON DELETE CASCADE,
    title              TEXT NOT NULL,
    source_type        TEXT,                        -- canonical | commentary | ...
    text_uri           TEXT,
    metadata           JSONB,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_persona_corpus_docs_version ON persona_corpus_docs(persona_version_id);
