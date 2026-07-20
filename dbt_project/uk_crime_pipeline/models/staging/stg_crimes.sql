select
    crime_id,
    (month || '-01')::date as month,
    reported_by,
    falls_within,
    longitude,
    latitude,
    location,
    lsoa_code,
    lsoa_name,
    crime_type,
    last_outcome_category,
    context
from {{ source('raw', 'raw_crimes') }}