-- 009_jobs.sql  (design §8.18)

CREATE TABLE jobs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id   UUID REFERENCES projects(id) ON DELETE CASCADE,
    episode_id   UUID REFERENCES episodes(id) ON DELETE CASCADE,
    -- source_ingestion | claim_extraction | embedding | episode_planning
    -- | script_generation | script_qa | voice_direction | audio_render
    -- | audio_mix | export_package
    job_type     TEXT NOT NULL,
    -- queued | running | completed | failed | canceled  (design §17.1)
    status       TEXT NOT NULL DEFAULT 'queued',
    progress     NUMERIC NOT NULL DEFAULT 0,
    input_json   JSONB,
    output_json  JSONB,
    error_json   JSONB,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at   TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_jobs_project_id ON jobs(project_id);
CREATE INDEX idx_jobs_episode_id ON jobs(episode_id);
CREATE INDEX idx_jobs_status ON jobs(status);
