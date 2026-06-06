-- 010_feedback.sql  (design §8.19)

CREATE TABLE feedback_events (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID REFERENCES users(id) ON DELETE SET NULL,
    project_id    UUID REFERENCES projects(id) ON DELETE CASCADE,
    episode_id    UUID REFERENCES episodes(id) ON DELETE CASCADE,
    target_type   TEXT NOT NULL,                   -- episode | script_segment | audio | persona ...
    target_id     UUID,
    feedback_type TEXT NOT NULL,                   -- thumbs | tag | comment
    rating        INT,                             -- e.g. -1 / +1, or 1..5
    tags          JSONB,
    comment       TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_feedback_events_project_id ON feedback_events(project_id);
CREATE INDEX idx_feedback_events_episode_id ON feedback_events(episode_id);
