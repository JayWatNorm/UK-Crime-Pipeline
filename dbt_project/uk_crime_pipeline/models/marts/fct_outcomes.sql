{{ config(materialized='table') }}

select
    id,
    crime_id,
    month,
    reported_by,
    falls_within,
    longitude,
    latitude,
    location,
    lsoa_code,
    lsoa_name,
    outcome_type,
    ingested_at
from {{ ref('stg_outcomes') }}