import subprocess
from datetime import datetime, timezone

from airflow.decorators import dag, task


@dag(
    schedule="@monthly",
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
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
            # check=False so stdout/stderr get printed into the Airflow task
            # log before the failure is raised -- check_returncode() below
            # does the actual failing.
            result = subprocess.run(
                cmd + ["--project-dir", project_dir, "--profiles-dir", profiles_dir],
                capture_output=True,
                text=True,
                check=False,
            )
            print(result.stdout)
            print(result.stderr)
            result.check_returncode()

    run_ingest() >> run_dbt_build()


crime_pipeline_dag()