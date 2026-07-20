"""Routine to download the latest.zip file from the
UK Police Data API and save it to the specified path."""
from ast import If
import os
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
download_file = os.path.join(script_dir, "..", "ingestion", "downloads", "latest.zip")
download_path = os.path.join(script_dir, "..", "ingestion", "downloads")
zip_path = os.path.join(script_dir, "..", "ingestion", "downloads", "latest")
doZip = False
doPGLoad = False

now = datetime.now()
months = []
year, month = now.year, now.month

for i in range(38):
    months.append(f"{year}-{month:02d}")
    month -= 1
    if month == 0:
        month = 12
        year -= 1

def blank_to_none(value):
    return value if value != '' else None

def fnc_download(dlpath):
    """Download the latest.zip file from the UK Police Data API."""
    response = requests.get("https://data.police.uk/data/archive/latest.zip",
                             stream=True, timeout=300)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"Error downloading file: {e}")
        return 1

    with open(dlpath, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return 0

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
        FN_RESULT = fnc_download(download_file)
        print("File downloaded successfully:" if FN_RESULT == 0 else "File download failed:", download_file)
else:
    print("File does not exist, downloading:", download_file)
    FN_RESULT = fnc_download(download_file)
    print("File downloaded successfully:" if FN_RESULT == 0 else "File download failed:", download_file)

print("Download section complete at:", datetime.now())

if doZip:
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
else:
    print("Zip extraction skipped as doZip is set to False.")


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



if doPGLoad:
    conn = psycopg2.connect(host=db_host, port=db_port, dbname=db_name, user=db_user, password=db_password)
    cursor = conn.cursor()
    for year_month in months:
        print("Loading data for month:", year_month)
        y, m = map(int, year_month.split('-'))
        files = load_month(y, m)
        if files is None:
            continue
        load_street_to_db(year_month, files["street"], cursor)
        conn.commit()
        print(f"Committed {year_month}")

    cursor.close()
    conn.close()
else:
    print("PostgreSQL load skipped as doPGLoad is set to False.")