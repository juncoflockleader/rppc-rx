-- 000_apply_all.sql
-- Convenience runner that applies every migration in order inside one transaction.
--   psql "$DATABASE_URL" -f migrations/000_apply_all.sql
-- For real environments use a migration tool (alembic / sqitch / dbmate) instead;
-- these files are plain SQL so any tool can adopt them.

-- \ir includes relative to THIS file, so it works regardless of the CWD psql
-- was launched from.
\set ON_ERROR_STOP on
BEGIN;

\ir 001_extensions.sql
\ir 002_users.sql
\ir 003_projects.sql
\ir 004_sources.sql
\ir 005_personas.sql
\ir 006_episodes.sql
\ir 007_scripts.sql
\ir 008_audio.sql
\ir 009_jobs.sql
\ir 010_feedback.sql

COMMIT;
