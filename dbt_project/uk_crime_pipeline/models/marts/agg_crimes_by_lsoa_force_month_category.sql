{{ config(materialized='table') }}

select
    count(crime_id) as crimes,
    month,
    lsoa_code,
    lsoa_name,
    falls_within,
    reported_by,
    crime_type
from {{ ref('fct_crimes') }}
group by month,
    lsoa_code,
    lsoa_name,
    falls_within,
    reported_by,
    crime_type