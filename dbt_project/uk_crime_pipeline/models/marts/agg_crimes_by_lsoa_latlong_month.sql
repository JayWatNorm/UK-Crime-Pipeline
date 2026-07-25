{{ config(materialized='table') }}

select
    count(crime_id) as crimes,
    lsoa_code,
    month,
    round(avg(longitude), 4) as longitude,
    round(avg(latitude), 4) as latitude
from {{ ref('fct_crimes') }}
group by lsoa_code, month