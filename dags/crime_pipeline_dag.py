from airflow.decorators import dag, task
from datetime import datetime

@dag(
    schedule="@monthly",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["crime-pipeline"],
)
def crime_pipeline_dag():

    @task
    def run_ingest():
        from ingestion.ingest import main
        main()

    run_ingest()

crime_pipeline_dag()