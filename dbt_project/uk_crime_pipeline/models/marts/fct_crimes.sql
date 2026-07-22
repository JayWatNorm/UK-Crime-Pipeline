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
    crime_type,
    last_outcome_category
from {{ ref('stg_crimes') }}