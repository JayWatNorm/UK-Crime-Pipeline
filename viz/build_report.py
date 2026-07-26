"""Load report data from the crime marts and render the static HTML report."""
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

import charts

load_dotenv()

db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")

# Anchored to this file rather than the working directory, so the script
# behaves the same run from the repo root, from viz/, or from Airflow.
VIZ_DIR = Path(__file__).parent
TEMPLATE_DIR = VIZ_DIR / "templates"
OUTPUT_DIR = VIZ_DIR / "output"

MIN_BASELINE = 20


def get_connection():
    return psycopg2.connect(host=db_host, port=db_port, dbname=db_name,
                            user=db_user, password=db_password)


def get_map_data(conn, min_baseline=MIN_BASELINE):
    sql = """
        SELECT
            lsoa_code,
            cy_crimes,
            ly_crimes,
            crime_change,
            crime_change_pct,
            longitude,
            latitude,
            comparison_period
        FROM agg_crimes_by_lsoa_ytd_vs_prior_year
        WHERE ly_crimes >= %(min_baseline)s
    """
    with conn.cursor() as cur:
        cur.execute(sql, {"min_baseline": min_baseline})
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]

    map_data = pd.DataFrame(rows, columns=columns)

    # Postgres numeric comes back as Decimal, which pandas holds as object
    # dtype. Plotly then treats the colour column as categorical rather than
    # continuous, so these need to be real floats before charting.
    for column in ("longitude", "latitude", "crime_change_pct"):
        map_data[column] = map_data[column].astype(float)

    return map_data


def render_report(context):
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    template = env.get_template("report.html.j2")

    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / "report.html"
    output_path.write_text(template.render(**context), encoding="utf-8")

    return output_path


def main():
    conn = get_connection()
    try:
        map_data = get_map_data(conn)
    finally:
        conn.close()

    if map_data.empty:
        print("No rows returned - nothing to render.")
        return

    comparison_period = map_data["comparison_period"].iloc[0]
    print(f"Rows: {map_data.shape[0]}, columns: {map_data.shape[1]}")
    print(comparison_period)

    change_map = charts.build_change_map(map_data)

    improved = int((map_data["crime_change_pct"] < 0).sum())
    worsened = int((map_data["crime_change_pct"] > 0).sum())

    context = {
        "title": "Change in recorded crime by neighbourhood",
        "comparison_period": comparison_period,
        "map_html": charts.figure_to_html(change_map),
        "min_baseline": MIN_BASELINE,
        "generated_at": datetime.now().strftime("%d %B %Y"),
        "stats": [
            {"value": f"{map_data.shape[0]:,}", "label": "Neighbourhoods mapped"},
            {"value": f"{improved:,}", "label": "Recorded fewer crimes"},
            {"value": f"{worsened:,}", "label": "Recorded more crimes"},
        ],
    }

    output_path = render_report(context)
    print(f"Report written to {output_path}")


if __name__ == "__main__":
    main()
