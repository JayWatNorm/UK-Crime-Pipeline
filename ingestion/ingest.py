"""Routine to download the latest.zip file from the 
UK Police Data API and save it to the specified path."""
import os
from datetime import datetime
import requests

script_dir = os.path.dirname(os.path.abspath(__file__))
download_file = os.path.join(script_dir, "..", "ingestion", "downloads", "latest.zip")
download_path = os.path.join(script_dir, "..", "ingestion", "downloads")


def fnc_download(dlpath):
    """Function to download the latest.zip file from the 
UK Police Data API and save it to the specified path."""
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

#check if the dir exists, if not create it
if os.path.exists(download_path):
    print("Download path exists:", download_path)
else:
    os.makedirs(download_path)
    print("Created download path:", download_path)
#check if the file exists, then verify it has been downloaded today. If not download it.
if os.path.exists(download_file):
    print("Download file exists:", download_file)
    if datetime.fromtimestamp(os.stat(download_file).st_mtime).date() == datetime.now().date():
        print ("File already downloaded today:",
               download_file,datetime.fromtimestamp(os.stat(download_file).st_mtime).date())
    else:
        print ("File exists but not downloaded today, downloading again:", download_file)
        FN_RESULT = fnc_download(download_file)
        if FN_RESULT == 0:
            print("File downloaded successfully:", download_file)
        else:
            print("File download failed:", download_file)

else:
    print ("File does not exist, downloading:", download_file)
    FN_RESULT = fnc_download(download_file)
    if FN_RESULT == 0:
        print("File downloaded successfully:", download_file)
    else:
        print("File download failed:", download_file)

print ("end")
