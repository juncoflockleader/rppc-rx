-- 014_script_qa.sql  (design §11.6, §19.5)
-- First-class safety gate on a script version (the audio renderer in M7 refuses
-- to run when safety_status = 'high_risk'), plus a rolled-up QA summary for the
-- panel. qa_reports (per-dimension detail) already exists from §8.15.

ALTER TABLE script_versions
    ADD COLUMN IF NOT EXISTS safety_status TEXT NOT NULL DEFAULT 'unknown',
    -- unknown | ok | needs_review | high_risk
    ADD COLUMN IF NOT EXISTS qa_summary JSONB;
