-- 007_scripts.sql  (design §8.12 – §8.15)

-- script_versions -----------------------------------------------------------
CREATE TABLE script_versions (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id                UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    version                   INT NOT NULL,
    source_discussion_plan_id UUID REFERENCES discussion_plans(id) ON DELETE SET NULL,
    status                    TEXT NOT NULL DEFAULT 'draft',
    total_estimated_seconds   INT,
    -- safety gate before audio render (design §19.5): ok | needs_review | high_risk
    metadata                  JSONB,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (episode_id, version)
);

CREATE INDEX idx_script_versions_episode_id ON script_versions(episode_id);

-- script_segments -----------------------------------------------------------
CREATE TABLE script_segments (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_version_id         UUID NOT NULL REFERENCES script_versions(id) ON DELETE CASCADE,
    episode_id                UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    segment_index             INT NOT NULL,
    beat_id                   TEXT,
    speaker_persona_version_id UUID REFERENCES persona_versions(id),
    speaker_label             TEXT NOT NULL,
    text                      TEXT NOT NULL,
    estimated_seconds         INT,
    delivery                  JSONB,                -- voice direction metadata
    qa_json                   JSONB,
    status                    TEXT NOT NULL DEFAULT 'draft',
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (script_version_id, segment_index)
);

CREATE INDEX idx_script_segments_script_version_id ON script_segments(script_version_id);
CREATE INDEX idx_script_segments_episode_id ON script_segments(episode_id);

-- segment_evidence_links ----------------------------------------------------
CREATE TABLE segment_evidence_links (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_segment_id     UUID NOT NULL REFERENCES script_segments(id) ON DELETE CASCADE,
    -- source_material | persona_canon | host_bridge | creative_bridge | unsupported_or_needs_review
    evidence_type         TEXT NOT NULL,
    source_claim_id       UUID REFERENCES source_claims(id) ON DELETE SET NULL,
    source_chunk_id       UUID REFERENCES source_chunks(id) ON DELETE SET NULL,
    persona_corpus_doc_id UUID REFERENCES persona_corpus_docs(id) ON DELETE SET NULL,
    concept               TEXT,
    confidence            NUMERIC,
    notes                 TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_segment_evidence_links_segment_id ON segment_evidence_links(script_segment_id);

-- qa_reports ----------------------------------------------------------------
CREATE TABLE qa_reports (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id        UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    script_version_id UUID REFERENCES script_versions(id) ON DELETE CASCADE,
    -- source_grounding | persona_fidelity | anachronism | safety | dialogue_quality | audio_readiness
    report_type       TEXT NOT NULL,
    score_json        JSONB NOT NULL,
    warnings          JSONB,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_qa_reports_script_version_id ON qa_reports(script_version_id);
