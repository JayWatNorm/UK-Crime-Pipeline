import os
import subprocess
import sys

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

    @task
    def run_dbt_build():
        project_dir = "/opt/airflow/project/dbt_project"
        profiles_dir = "/opt/airflow/dbt_profiles"
        for cmd in (["dbt", "deps"], ["dbt", "build"]):
            result = subprocess.run(
                cmd + ["--project-dir", project_dir, "--profiles-dir", profiles_dir],
                capture_output=True,
                text=True,
            )
            print(result.stdout)
            print(result.stderr)
            result.check_returncode()

    run_ingest() >> run_dbt_build()


crime_pipeline_dag()