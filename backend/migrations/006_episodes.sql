-- 006_episodes.sql  (design §8.9 – §8.11)

-- episodes ------------------------------------------------------------------
CREATE TABLE episodes (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id              UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title                   TEXT,
    target_language         TEXT NOT NULL DEFAULT 'en',
    target_duration_seconds INT NOT NULL,
    format                  TEXT NOT NULL DEFAULT 'philosophical_dialogue',
    audience                TEXT,
    style                   TEXT,
    status                  TEXT NOT NULL DEFAULT 'draft',
    settings                JSONB,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_episodes_project_id ON episodes(project_id);

-- episode_personas ----------------------------------------------------------
CREATE TABLE episode_personas (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id         UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    persona_version_id UUID NOT NULL REFERENCES persona_versions(id),
    role               TEXT NOT NULL,               -- host | guest | student | critic
    speaker_label      TEXT NOT NULL,               -- HOST | LAOZI | BUDDHA ...
    sort_order         INT NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (episode_id, speaker_label)
);

CREATE INDEX idx_episode_personas_episode_id ON episode_personas(episode_id);

-- discussion_plans ----------------------------------------------------------
CREATE TABLE discussion_plans (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    version    INT NOT NULL DEFAULT 1,
    plan_json  JSONB NOT NULL,
    status     TEXT NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (episode_id, version)
);

CREATE INDEX idx_discussion_plans_episode_id ON discussion_plans(episode_id);
