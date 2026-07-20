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

CREATE TABLE IF NOT EXISTS checklog (
    id                     SERIAL PRIMARY KEY,
    crime_last_updated     TIMESTAMPTZ NOT NULL,
    status                 TEXT NOT NULL,  -- 'success' or 'failure' -- one row written per run, not just on success
    error_message          TEXT,           -- populated when status = 'failure', else NULL
    checked_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Outcomes: shares street's location columns but replaces crime_type/
-- last_outcome_category/context with a single outcome_type -- confirmed
-- against a real downloaded outcomes CSV. No FK to raw_crimes: outcomes
-- rows can reference crimes reported many months earlier, outside this
-- archive's window, so orphaned crime_id values are expected, not an error.
CREATE TABLE IF NOT EXISTS raw_outcomes (
    id                     SERIAL PRIMARY KEY,
    crime_id               TEXT,
    month                  TEXT NOT NULL,  -- 'YYYY-MM' as published, same as raw_crimes
    reported_by            TEXT NOT NULL,
    falls_within           TEXT NOT NULL,
    longitude              NUMERIC,
    latitude               NUMERIC,
    location               TEXT,
    lsoa_code              TEXT,
    lsoa_name              TEXT,
    outcome_type           TEXT,
    ingested_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_raw_outcomes_month ON raw_outcomes (month);

-- Stop-and-search: a genuinely different dataset (person stopped, not a
-- crime record) -- confirmed against a real downloaded stop-and-search CSV.
-- Note the source file has no Month column at all, only a full Date --
-- `month` here must be set from the year_month the ingestion loop already
-- knows, not parsed out of any CSV field.
CREATE TABLE IF NOT EXISTS raw_stop_and_search (
    id                          SERIAL PRIMARY KEY,
    month                       TEXT NOT NULL,  -- set from year_month at load time, not sourced from the CSV
    type                        TEXT,
    date                        TEXT,           -- kept as published; cast to a real timestamp in staging
    part_of_policing_operation  TEXT,
    policing_operation          TEXT,
    latitude                    NUMERIC,
    longitude                   NUMERIC,
    gender                      TEXT,
    age_range                   TEXT,
    self_defined_ethnicity      TEXT,
    officer_defined_ethnicity   TEXT,
    legislation                 TEXT,
    object_of_search            TEXT,
    outcome                     TEXT,
    outcome_linked_to_object_of_search  TEXT,
    removal_of_more_than_outer_clothing TEXT,
    ingested_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_raw_stop_and_search_month ON raw_stop_and_search (month);


