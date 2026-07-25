# UK Crime Data Pipeline

[github.com/JayWatNorm/UK-Crime-Pipeline](https://github.com/JayWatNorm/UK-Crime-Pipeline)

A data engineering portfolio project: ingests, models, orchestrates, and visualizes
UK police street-level crime data at national scale.

Follow-up to [Comfort Compass](../Comfort-Compass), deliberately targeting the gaps
that project didn't cover:

- **Orchestration** — real DAG-based scheduling with retries and historical backfill (Airflow)
- **CI/CD** — automated testing on every code change (GitHub Actions)
- **Scale** — a genuinely large, multi-year national dataset (~19M+ rows)
- **Visualization** — a polished but intentionally lightweight output layer

## Data source

[data.police.uk](https://data.police.uk/data/) — street-level crime archives
published by police forces across England, Wales, and Northern Ireland. Each
archive is a rolling ~3-year snapshot rather than a single month's data — see
`docs/data-source-notes.md` for the full schema, archive structure, and
backfill approach.

## Stack

| Layer | Choice |
|---|---|
| Storage | PostgreSQL (Docker) |
| Ingestion | Python |
| Orchestration | Apache Airflow (Docker) |
| Transformation | dbt |
| CI/CD | GitHub Actions |
| Visualization | Plotly + Jinja2 → static HTML |
| Containerization | Docker Compose |

Full architecture, phased task breakdown, and design rationale live in
`uk-crime-pipeline-project-plan.md` (project planning doc, kept outside this repo).

## Status

- Data source schema confirmed against a real download (`docs/data-source-notes.md`)
- Postgres + Docker foundation in place, raw table DDL written for all three
  source datasets (`raw_crimes`, `raw_outcomes`, `raw_stop_and_search`)
- Ingestion complete — full ~3-year backfill across all three datasets, with
  idempotent per-month loads, atomic rollback, and status tracking in `checklog`
- dbt transformation layer complete — staging models for all three sources,
  fact and aggregate marts, grain/not-null/accepted-values tests passing
- Airflow orchestration complete — `run_ingest` → `run_dbt_build`, running
  monthly
- Visualization and CI/CD not yet started

See the companion progress tracker for full detail on where the build stands.

## Setup

```bash
cp .env.example .env   # fill in DB credentials
docker compose up -d   # brings up Postgres + Airflow
```

`.env` is the single source of truth for database connection details — both
`ingestion/ingest.py` and dbt read from it, so pointing it at a different
database is all that's needed to switch environments.

### Running dbt locally

dbt doesn't read `.env` files itself, so `run-dbt.ps1` loads it first and
passes through whatever arguments you give it:

```powershell
.\run-dbt.ps1 build
.\run-dbt.ps1 test
```

This is only needed for bare local runs. Inside Docker (and on the deployed
Airflow instance), connection details are set directly on the container, so
dbt is invoked normally there.

## Note

This project's Docker setup (Postgres container, image, volumes, `.env`) is
entirely separate from Comfort Compass's — no shared containers, networks,
or data between the two.
