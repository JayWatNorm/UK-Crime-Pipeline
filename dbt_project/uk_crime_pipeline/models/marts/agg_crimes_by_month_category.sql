{{ config(materialized='table') }}

select
    sum(crimes) as crimes,
    month,
    crime_type
from {{ ref('agg_crimes_by_lsoa_force_month_category') }}
group by month,
    crime_type