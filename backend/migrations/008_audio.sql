-- 008_audio.sql  (design §8.16 – §8.17)

-- audio_segments ------------------------------------------------------------
CREATE TABLE audio_segments (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_segment_id UUID NOT NULL REFERENCES script_segments(id) ON DELETE CASCADE,
    episode_id        UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    speaker_label     TEXT NOT NULL,
    tts_provider      TEXT NOT NULL,
    voice_id          TEXT NOT NULL,
    audio_uri         TEXT NOT NULL,
    duration_ms       INT,
    render_params     JSONB,
    status            TEXT NOT NULL DEFAULT 'rendered',  -- rendered | failed | stale
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audio_segments_script_segment_id ON audio_segments(script_segment_id);
CREATE INDEX idx_audio_segments_episode_id ON audio_segments(episode_id);

-- audio_mixes ---------------------------------------------------------------
-- final mix is a regenerable artifact, not the source of truth (design §9).
CREATE TABLE audio_mixes (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id        UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    script_version_id UUID NOT NULL REFERENCES script_versions(id) ON DELETE CASCADE,
    audio_uri         TEXT NOT NULL,
    duration_ms       INT,
    format            TEXT NOT NULL DEFAULT 'mp3',
    status            TEXT NOT NULL DEFAULT 'completed',
    metadata          JSONB,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audio_mixes_episode_id ON audio_mixes(episode_id);
