-- Raw layer DDL for UK Crime Pipeline.
-- Mirrors Comfort Compass's pattern: single schema, raw_-prefixed tables,
-- minimal typing here (dbt staging models handle real cleaning/casting).
-- Mounted via Postgres's own /docker-entrypoint-initdb.d/ hook (see
-- docker-compose.yml), so this runs automatically on first container start
-- against an empty data directory only -- it will NOT rerun on an existing
-- volume with data already in it.

CREATE TABLE IF NOT EXISTS raw_crimes (
    id                     SERIAL PRIMARY KEY,
    crime_id               TEXT,           -- one-way hash; confirmed blank on some rows per data.police.uk docs, so no uniqueness/not-null constraint here
    month                  TEXT NOT NULL,  -- 'YYYY-MM' as published; cast to a real date in staging
    reported_by            TEXT NOT NULL,
    falls_within           TEXT NOT NULL,
    longitude              NUMERIC,        -- nullable: anonymisation can zero these out or leave blank when no safe snap point is within 20km
    latitude               NUMERIC,
    location               TEXT,           -- e.g. "On or near Gwent Terrace" -- confirmed present against a real download
    lsoa_code              TEXT,
    lsoa_name              TEXT,
    crime_type             TEXT NOT NULL,  -- one of the 14 fixed categories -- see docs/data-source-notes.md
    last_outcome_category  TEXT,           -- latest outcome only, can be null if no outcome recorded yet
    context                TEXT,           -- currently always empty for new rows per data.police.uk, kept for completeness
    ingested_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Ingestion does a delete+insert per month (idempotent re-runs, per the
-- project plan's Phase 3 design) -- this index makes that WHERE month = '...'
-- delete, and later per-month queries, fast at national/multi-year scale.
CREATE INDEX IF NOT EXISTS idx_raw_crimes_month ON raw_crimes (month);
