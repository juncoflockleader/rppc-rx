-- 000_apply_all.sql
-- Convenience runner that applies every migration in order inside one transaction.
--   psql "$DATABASE_URL" -f migrations/000_apply_all.sql
-- For real environments use a migration tool (alembic / sqitch / dbmate) instead;
-- these files are plain SQL so any tool can adopt them.

\set ON_ERROR_STOP on
BEGIN;

\i 001_extensions.sql
\i 002_users.sql
\i 003_projects.sql
\i 004_sources.sql
\i 005_personas.sql
\i 006_episodes.sql
\i 007_scripts.sql
\i 008_audio.sql
\i 009_jobs.sql
\i 010_feedback.sql

COMMIT;
