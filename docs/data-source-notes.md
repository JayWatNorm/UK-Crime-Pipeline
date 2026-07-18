# Data Source Notes — data.police.uk

Phase 1 deliverable (project plan §Phase 1). Findings from data.police.uk's
own documentation and a live API sample, gathered 2026-07-18. **Not yet
cross-checked against an actual downloaded CSV** — see caveat at the bottom.

## CSV columns (street-level crime files)

Per the official [About page](https://data.police.uk/about/#columns):

| Column | Notes |
|---|---|
| Crime ID | One-way hash of the offence reference. Can be blank for some records. |
| Month | Truncated to `YYYY-MM` — no day-level granularity. |
| Reported by | Force that supplied the data. |
| Falls within | Currently always the same as "Reported by" — the docs note this is under review and may change. |
| Longitude / Latitude | Anonymised — snapped to the nearest of ~760k pre-defined map points (street centres, parks, named premises), not the real location. Zeroed out if nearest snap point is >20km away. |
| Location | Not explicitly named in the About page's column table, but corroborated by the live JSON API sample (`location.street.name`, e.g. "On or near Roman Street") — expect an equivalent free-text column in the CSV. **Confirm exact column name against a real file.** |
| LSOA code / LSOA name | 2021 LSOA boundaries (ONS). |
| Crime type | One of 14 fixed categories (see below) — confirmed live via the API. |
| Last outcome category | Most recent outcome only, not full history. One of ~28 fixed values (see below). |
| Context | Free text for forces to add detail. Empty for all newly added rows currently. |

## Crime categories (confirmed live, 2026-04)

`all-crime` (meta), `anti-social-behaviour`, `bicycle-theft`, `burglary`,
`criminal-damage-arson`, `drugs`, `other-theft`, `possession-of-weapons`,
`public-order`, `robbery`, `shoplifting`, `theft-from-the-person`,
`vehicle-crime`, `violent-crime` (labelled "Violence and sexual offences"),
`other-crime`. Good candidate list for a dbt `accepted_values` test on
`crime_type`.

## Outcome categories (confirmed live via API docs)

~28 fixed values (e.g. `no-further-action`, `charged`, `imprisoned`,
`under-investigation`, `status-update-unavailable` — full list in the API
docs). Also a good `accepted_values` candidate for `last_outcome_category`.

## Archive structure — the big finding

**Each monthly archive zip is a rolling ~3-year snapshot, not a single
month's data.** E.g. `2026-05.zip` (1.6GB) contains everything from June
2023 to May 2026. This contradicts the original plan doc's assumption of
one-month-per-zip.

data.police.uk's own guidance: *"With the exception of the latest month's
archive, the data on this page is out of date and should not be used."*
They recommend the [custom download page](https://data.police.uk/data/) or
[JSON API](https://data.police.uk/docs/) for most purposes, and reserve the
bulk archive for the latest snapshot.

### Decision: backfill range and approach

Confirmed with the user (2026-07-18):

- **Download `latest.zip` once** — it already contains the full ~3-year
  trailing window, satisfying the "genuinely data-heavy" goal without
  needing to touch any older, publisher-flagged-as-stale archives.
- **Airflow backfill still works exactly as designed.** `catchup=True`
  gives one DAG run per historical month; each run's `load_raw` task
  filters the single downloaded file down to its own month and does an
  idempotent delete+insert on that month's partition (per Phase 3). Airflow
  genuinely schedules, retries, and backfills — it just doesn't need a
  fresh multi-GB download per historical month to do so.
- **Going forward**, each new month's DAG run downloads that month's
  freshly-published archive (same rolling-window shape) and loads the new
  month's rows. Worth also re-checking a few recent trailing months on each
  run, since the docs note crimes can be retroactively reclassified —
  worth deciding later whether to re-load a small trailing window each run
  or trust the initial load.
- **Full history back to 2010 rejected** — would require stitching together
  years of old archive snapshots the publisher explicitly says not to rely
  on, for a portfolio project where a clean ~3 years is already
  "genuinely data-heavy" enough.

### Geographic scope

Effectively answered by the above: the bulk archive already bundles **all
UK forces** together in one zip (one CSV per force inside it) — there's no
smaller "subset" version at this bulk level. ~1.6GB either way.

## Caveat — not yet verified against a real file

Everything above comes from data.police.uk's live documentation pages and
one live JSON API call, not an actual downloaded CSV — the 1.6GB archive
isn't practical to pull through the sandboxed environment this was
researched in (direct downloads to data.police.uk are network-blocked
there). Before writing the ingestion script (Phase 3) or raw table DDL,
do a real download and confirm:

- Exact column header names/order (especially whether "Location" exists
  and what it's actually called)
- Whether "Crime ID" is ever genuinely blank, and how that should be
  handled (nullable? excluded from a uniqueness test?)
- Encoding, line endings, and whether a trailing blank line/row exists
- Whether outcome data is present per-row or needs the separate "include
  outcomes data" option from the custom download page
