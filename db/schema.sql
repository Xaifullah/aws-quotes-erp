-- Phase 6 schema for the SQS → consumer → RDS pipeline.
-- Idempotent: safe to re-run with `psql -f db/schema.sql`.

CREATE TABLE IF NOT EXISTS scrape_runs (
    run_id          TEXT PRIMARY KEY,
    source          TEXT        NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL,
    last_message_at TIMESTAMPTZ NOT NULL,
    quote_count     INTEGER     NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS quotes (
    id           TEXT PRIMARY KEY,           -- QuoteCleaner._make_id: sha256(author::text)[:16]
    text         TEXT        NOT NULL,
    author       TEXT        NOT NULL,
    tags         TEXT[]      NOT NULL DEFAULT '{}',
    processed_at TIMESTAMPTZ NOT NULL,
    run_id       TEXT REFERENCES scrape_runs (run_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS quotes_author_idx ON quotes (author);
CREATE INDEX IF NOT EXISTS quotes_tags_idx   ON quotes USING GIN (tags);
CREATE INDEX IF NOT EXISTS scrape_runs_last_message_idx ON scrape_runs (last_message_at DESC);
