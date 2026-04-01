-- Run once on Postgres (e.g. Supabase SQL editor) after deploying backend code that expects this column.
ALTER TABLE reports ADD COLUMN IF NOT EXISTS viability_summary JSONB;
