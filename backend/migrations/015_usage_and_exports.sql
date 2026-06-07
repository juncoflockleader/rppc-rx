-- 015_usage_and_exports.sql  (design §20.3-20.4 cost/debug; §6.8 export service)

-- Per-call cost + debug trace (§20.4). episode/project are nullable so API-path
-- calls (e.g. a one-off segment rewrite) still record. No full source text here.
CREATE TABLE usage_events (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind           TEXT NOT NULL,          -- llm | tts | embedding
    task_name      TEXT,
    prompt_version TEXT,
    model          TEXT,
    input_tokens   INT,
    output_tokens  INT,
    char_count     INT,
    duration_ms    INT,                    -- audio produced (tts)
    latency_ms     INT,                    -- call latency
    project_id     UUID REFERENCES projects(id) ON DELETE SET NULL,
    episode_id     UUID REFERENCES episodes(id) ON DELETE SET NULL,
    metadata       JSONB,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_usage_events_episode ON usage_events(episode_id);
CREATE INDEX idx_usage_events_project ON usage_events(project_id);

-- Export packages (§2.4): a zip of transcript / SRT / show notes / evidence
-- report / audio, written to object storage.
CREATE TABLE exports (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id        UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    script_version_id UUID REFERENCES script_versions(id) ON DELETE SET NULL,
    package_uri       TEXT NOT NULL,
    format            TEXT NOT NULL DEFAULT 'zip',
    manifest          JSONB,
    status            TEXT NOT NULL DEFAULT 'completed',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_exports_episode ON exports(episode_id);
