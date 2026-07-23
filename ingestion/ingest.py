"""Routine to download the latest.zip file from the
UK Police Data API and save it to the specified path."""
import os
import sys
from datetime import datetime
import shutil
import psycopg2
from psycopg2.extras import execute_values
import requests
import zipfile
import csv
from dotenv import load_dotenv
load_dotenv()

db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
script_dir = os.path.dirname(os.path.abspath(__file__))
# Defaults to a folder alongside this script, same as always -- but
# overridable via DOWNLOAD_DIR. Needed when this script runs as a
# different user than whoever owns the mounted source tree (e.g. the
# shared homelab Airflow container), since writing into -- and deleting
# from -- the source directory itself then fails with a permissions
# error (rmtree/makedirs need write access to the *parent* directory,
# not just the target one).
download_path = os.getenv("DOWNLOAD_DIR", os.path.join(script_dir, "..", "ingestion", "downloads"))
download_file = os.path.join(download_path, "latest.zip")
zip_path = os.path.join(download_path, "latest")

def main():
    try:
        response = requests.get("https://data.police.uk/api/crime-last-updated", timeout=10)
        response.raise_for_status()
        lastUpdated_date = response.json()['date']
    except (requests.exceptions.RequestException, KeyError, ValueError) as e:
        print(f"Could not check crime-last-updated: {e}")
        sys.exit(1)

    print(f"Crime last updated: {lastUpdated_date}")

    doZip = False
    doPGLoad = False
    now = datetime.now()
    months = []
    year, month = now.year, now.month

    conn = psycopg2.connect(host=db_host, port=db_port, dbname=db_name, user=db_user, password=db_password)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM checklog WHERE status = 'success' ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    print(row)

    if row is None or row[1].date() != datetime.strptime(lastUpdated_date, "%Y-%m-%d").date():  # if more recent file then nuke the path
        doZip = True
        doPGLoad = True
        if os.path.exists(download_path):
            shutil.rmtree(download_path)
        download_result = fncdownload_file(lastUpdated_date)
        if download_result != 0:
            doZip = False
            doPGLoad = False

    if doZip:
        for i in range(38):
            months.append(f"{year}-{month:02d}")
            month -= 1
            if month == 0:
                month = 12
                year -= 1

    if doZip:
        try:
            if os.path.exists(zip_path):
                print("Zip path exists, removing:", zip_path)
                shutil.rmtree(path=zip_path)
            else:
                print("Directory doesn't exist:", zip_path)
            print("Creating zip path:", zip_path)
            os.makedirs(zip_path, exist_ok=True)
            with zipfile.ZipFile(download_file, 'r') as zip_ref:
                zip_ref.extractall(zip_path)
                print("Extracted zip file to:", zip_path)
        except Exception as e:
            print(f"Zip extraction failed: {e}")
            write_checklog("failure", lastUpdated_date, f"zip extraction failed: {e}")
            doPGLoad = False
            doZip = False
    else:
        print("Zip extraction skipped as doZip is set to False.")

    if doPGLoad:
        conn = psycopg2.connect(host=db_host, port=db_port, dbname=db_name, user=db_user, password=db_password)
        cursor = conn.cursor()
        all_succeeded = True
        errors = []

        for year_month in months:
            print("Loading data for month:", year_month)
            y, m = map(int, year_month.split('-'))
            files = load_month(y, m)
            if files is None:
                continue

            try:
                load_street_to_db(year_month, files["street"], cursor)
                load_outcomes_to_db(year_month, files["outcomes"], cursor)
                load_search_to_db(year_month, files["stop_and_search"], cursor)
                conn.commit()
                print(f"Committed {year_month}")
            except Exception as e:
                conn.rollback()
                all_succeeded = False
                errors.append(f"{year_month}: {e}")
                print(f"Failed to load {year_month}, rolled back: {e}")

        cursor.close()
        conn.close()

        status = "success" if all_succeeded else "failure"
        error_message = "; ".join(errors) if errors else None
        write_checklog(status, lastUpdated_date, error_message)

        if all_succeeded:
            shutil.rmtree(download_path)
            print("All months loaded successfully — checklog recorded success, downloads cleaned up.")
        else:
            print("At least one month failed — checklog recorded failure, downloads kept for retry.")

    else:
        print("PostgreSQL load skipped as doPGLoad is set to False.")


def blank_to_none(value):
    return value if value != '' else None

def write_checklog(status, last_updated, error_message=None):
    """Write one row to checklog for this run -- 'success' or 'failure',
    with an optional error_message. Used by both the zip-extraction step
    and the per-month DB load step, so every stage of the pipeline reports
    the same way. `last_updated` is passed in explicitly rather than read
    from a global, since lastUpdated_date now lives inside main()."""
    log_conn = psycopg2.connect(host=db_host, port=db_port, dbname=db_name, user=db_user, password=db_password)
    log_cursor = log_conn.cursor()
    log_cursor.execute(
        "INSERT INTO checklog (crime_last_updated, status, error_message) VALUES (%s, %s, %s)",
        (last_updated, status, error_message)
    )
    log_conn.commit()
    log_cursor.close()
    log_conn.close()

def fnc_download(dlpath, last_updated):
    """Download the latest.zip file from the UK Police Data API."""
    response = requests.get("https://data.police.uk/data/archive/latest.zip",
                             stream=True, timeout=300)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"Error downloading file: {e}")
        write_checklog("failure", last_updated, f"download failed: {e}")
        return 1

    with open(dlpath, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return 0

def fncdownload_file(lastUpdated_date):

    if os.path.exists(download_path):
        print("Download path exists:", download_path)
    else:
        os.makedirs(download_path)
        print("Created download path:", download_path)

    if os.path.exists(download_file):
        print("Download file exists:", download_file)
        if datetime.fromtimestamp(os.stat(download_file).st_mtime).date() == datetime.now().date():
            print("File already downloaded today:", download_file)
        else:
            print("File exists but not downloaded today, downloading again:", download_file)
            FN_RESULT = fnc_download(download_file, lastUpdated_date)
            if FN_RESULT != 0:
                print("File download failed:", download_file)
                return 1
            print("File downloaded successfully:", download_file)
    else:
        print("File does not exist, downloading:", download_file)
        FN_RESULT = fnc_download(download_file, lastUpdated_date)
        if FN_RESULT != 0:
            print("File download failed:", download_file)
            return 1
        print("File downloaded successfully:", download_file)

    print("Download section complete at:", datetime.now())
    return 0

def load_month(year, month):
    """Find the street/outcomes/stop-and-search files for a specific year and month.
    Returns None if that month isn't in the extracted archive, otherwise a dict
    of the three file lists."""
    month_path = os.path.join(zip_path, f"{year}-{month:02d}")

    if not os.path.exists(month_path):
        print(f"Data for {year}-{month:02d} does not exist in the extracted files.")
        return None
    stop_and_search = []
    street = []
    outcomes = []

    for item in os.listdir(month_path):
        item_path = os.path.join(month_path, item)
        if os.path.isfile(item_path):
            if "stop-and-search" in item:
                stop_and_search.append(item_path)
            elif "street" in item:
                street.append(item_path)
            elif "outcomes" in item:
                outcomes.append(item_path)
    return {"street": street, "outcomes": outcomes, "stop_and_search": stop_and_search}


def load_street_to_db(year_month, street_files, cursor):
    """Delete existing raw_crimes rows for this month, then insert fresh rows
    from every force's street CSV for that month, in one batched call per
    file rather than one execute() per row."""
    cursor.execute("DELETE FROM raw_crimes WHERE month = %s", (year_month,))

    insert_sql = (
        "INSERT INTO raw_crimes (crime_id, month, reported_by, falls_within, "
        "longitude, latitude, location, lsoa_code, lsoa_name, crime_type, "
        "last_outcome_category, context) VALUES %s"
    )

    for each in street_files:
        with open(each, 'r') as f:
            reader = csv.DictReader(f, delimiter=',')
            rows = [
                (blank_to_none(row['Crime ID']), blank_to_none(row['Month']), blank_to_none(row['Reported by']),
                 blank_to_none(row['Falls within']), blank_to_none(row['Longitude']), blank_to_none(row['Latitude']),
                 blank_to_none(row['Location']), blank_to_none(row['LSOA code']), blank_to_none(row['LSOA name']),
                 blank_to_none(row['Crime type']), blank_to_none(row['Last outcome category']), blank_to_none(row['Context']))
                for row in reader
            ]
        if rows:
            execute_values(cursor, insert_sql, rows, page_size=5000)
def load_outcomes_to_db(year_month, outcome_files, cursor):
    """Delete existing raw_outcomes rows for this month, then insert fresh rows
    from every force's street CSV for that month, in one batched call per
    file rather than one execute() per row."""
    cursor.execute("DELETE FROM raw_outcomes WHERE month = %s", (year_month,))

    insert_sql = (
        "INSERT INTO raw_outcomes (crime_id, month, reported_by, falls_within, "
        "longitude, latitude, location, lsoa_code, lsoa_name, outcome_type "
        ") VALUES %s"
    )

    for each in outcome_files:
        with open(each, 'r') as f:
            reader = csv.DictReader(f, delimiter=',')
            rows = [
                (blank_to_none(row['Crime ID']), blank_to_none(row['Month']), blank_to_none(row['Reported by']),
                 blank_to_none(row['Falls within']), blank_to_none(row['Longitude']), blank_to_none(row['Latitude']),
                 blank_to_none(row['Location']), blank_to_none(row['LSOA code']), blank_to_none(row['LSOA name']),
                 blank_to_none(row['Outcome type']))
                for row in reader
            ]
        if rows:
            execute_values(cursor, insert_sql, rows, page_size=5000)

def load_search_to_db(year_month, stop_and_search_files, cursor):
    """Delete existing raw_stop_and_search rows for this month, then insert fresh rows
    from every force's street CSV for that month, in one batched call per
    file rather than one execute() per row."""
    cursor.execute("DELETE FROM raw_stop_and_search WHERE month = %s", (year_month,))

    insert_sql = (
        "INSERT INTO raw_stop_and_search (month, type, date, "
        "part_of_policing_operation, policing_operation, latitude, longitude, gender, age_range, "
        "self_defined_ethnicity, officer_defined_ethnicity, legislation, object_of_search, outcome,"
        "outcome_linked_to_object_of_search, removal_of_more_than_outer_clothing) VALUES %s"
    )

    for each in stop_and_search_files:
        with open(each, 'r') as f:
            reader = csv.DictReader(f, delimiter=',')
            rows = [
                (year_month, blank_to_none(row['Type']),
                blank_to_none(row['Date']),blank_to_none(row['Part of a policing operation']),blank_to_none(row['Policing operation']),
                blank_to_none(row['Latitude']),blank_to_none(row['Longitude']),blank_to_none(row['Gender']),blank_to_none(row['Age range']),
                blank_to_none(row['Self-defined ethnicity']),blank_to_none(row['Officer-defined ethnicity']),blank_to_none(row['Legislation']),
                blank_to_none(row['Object of search']),blank_to_none(row['Outcome']),blank_to_none(row['Outcome linked to object of search']),
                blank_to_none(row['Removal of more than just outer clothing']))
                for row in reader
            ]
        if rows:
            execute_values(cursor, insert_sql, rows, page_size=5000)
if __name__ == "__main__":
    main()