# Shared image for ingestion + dbt (mirrors Comfort Compass's single-image
# pattern). Airflow itself runs from the official Airflow image, not this
# one — added as its own service in Phase 5.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "--version"]
