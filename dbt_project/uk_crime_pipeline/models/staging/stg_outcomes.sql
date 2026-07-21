select
    id,
    crime_id,
    (month || '-01')::date as month,
    reported_by,
    falls_within,
    longitude,
    latitude,
    location,
    lsoa_code,
    lsoa_name,
    outcome_type,
    ingested_at
from {{ source('raw', 'raw_outcomes') }}
