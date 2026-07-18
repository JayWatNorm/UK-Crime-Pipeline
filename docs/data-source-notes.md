# Data Source Notes — data.police.uk

Phase 1 deliverable (project plan §Phase 1). Findings from data.police.uk's
own documentation and a live API sample, gathered 2026-07-18, then
cross-checked by the user against a real downloaded CSV (custom download
page, Dyfed-Powys Police, May 2026) the same day — confirmed accurate, see
below.

## CSV columns (street-level crime files)

**Confirmed against a real downloaded CSV** — exact header row, in order:
`Crime ID, Month, Reported by, Falls within, Longitude, Latitude, Location,
LSOA code, LSOA name, Crime type, Last outcome category, Context`.

| Column | Notes |
|---|---|
| Crime ID | One-way hash of the offence reference, e.g. `4fb2c342...843806`. Docs say it can be blank on some records — not observed in the sample checked, but no not-null/unique constraint assumed in the raw DDL because of this. |
| Month | Truncated to `YYYY-MM` — no day-level granularity. Confirmed e.g. `2026-05`. |
| Reported by / Falls within | Force that supplied the data. Confirmed identical on every sampled row (e.g. both `Dyfed-Powys Police`) — matches the docs' note that these are currently always the same. |
| Longitude / Latitude | Anonymised — snapped to the nearest of ~760k pre-defined map points (street centres, parks, named premises), not the real location. Zeroed out if nearest snap point is >20km away. Confirmed real decimal values in the sample, e.g. `-1.907962, 52.493187`. |
| Location | Confirmed present, e.g. `On or near Westhorpe Grove`, `On or near Gwent Terrace`. |
| LSOA code / LSOA name | Confirmed, e.g. `E01033638` / `Birmingham 049F`, and `W01001468` / `Blaenau Gwent 005E` — both English (`E`) and Welsh (`W`) prefixes seen, as expected for a Welsh force. |
| Crime type | One of 14 fixed categories (see below) — confirmed live via the API and in the sample (`Violence and sexual offences`). |
| Last outcome category | Most recent outcome only, not full history. Confirmed in sample, e.g. `Investigation complete; no suspect identified`, `Under investigation`. |
| Context | Free text for forces to add detail. Empty on every sampled row, consistent with the docs saying it's currently always empty for new rows. |

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

## Postcode enrichment — considered, shelved

Raised after noticing rows have Longitude/Latitude but no postcode column:
could reverse-geocode lat/long → postcode (as Comfort Compass does with
`postcodes.io`). Shelved for now — two reasons: (1) at ~3 years/all-UK
scale this is a genuine batch geocoding job, not a quick enrichment step,
and (2) the published lat/long is already anonymised to the nearest of a
fixed set of "safe" points, so a derived postcode would describe the
anonymisation point, not necessarily where the crime happened — risks
implying false precision the plan deliberately avoids elsewhere. LSOA
already serves the "what area" purpose without that risk. Possible
deferred Phase 4/6 enrichment if revisited later.

## Remaining open item

Outcome data: the sample checked only used the default "include crime
data" option from the custom download page — haven't yet checked what the
separate "include outcomes data" checkbox adds (a full per-crime outcome
history file, per the About page) or whether the project needs it. Current
plan only uses `Last outcome category` from the main crime file, which is
sufficient for the marts the plan describes (`fct_crimes`,
`agg_crimes_by_force_month_category`, `agg_crimes_by_lsoa`) — revisit only
if outcome-history-specific analysis gets added to scope later.
