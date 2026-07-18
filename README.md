# UK Crime Data Pipeline

A data engineering portfolio project: ingests, models, orchestrates, and visualizes
UK police street-level crime data at national scale.

Follow-up to [Comfort Compass](../Comfort-Compass), deliberately targeting the gaps
that project didn't cover:

- **Orchestration** — real DAG-based scheduling with retries and historical backfill (Airflow)
- **CI/CD** — automated testing on every code change (GitHub Actions)
- **Scale** — a genuinely large, multi-year national dataset (~19M+ rows)
- **Visualization** — a polished but intentionally lightweight output layer

## Data source

[data.police.uk](https://data.police.uk/data/) — monthly street-level crime archives
published by police forces across England, Wales, and Northern Ireland.

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

Early scaffolding — see the companion progress tracker for where the build
actually stands.

## Setup

```bash
cp .env.example .env   # fill in DB credentials
docker compose up -d   # brings up Postgres
```

More services (dbt, Airflow) are added as later build phases land — see the
project plan's phased breakdown.

## Note

This project's Docker setup (Postgres container, image, volumes, `.env`) is
entirely separate from Comfort Compass's — no shared containers, networks,
or data between the two.
