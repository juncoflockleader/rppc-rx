-- 013_role_context.sql  (design §11.3)
-- Role context cards are the key intermediate product of episode planning: for
-- each speaker, what they agree with, push back on, may not say, and which
-- source claims / persona concepts are relevant this episode. Stored per episode
-- + speaker, versioned so regeneration keeps history.

CREATE TABLE role_context_cards (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id         UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    persona_version_id UUID NOT NULL REFERENCES persona_versions(id),
    speaker_label      TEXT NOT NULL,
    version            INT NOT NULL DEFAULT 1,
    card_json          JSONB NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (episode_id, speaker_label, version)
);

CREATE INDEX idx_role_context_cards_episode ON role_context_cards(episode_id);
