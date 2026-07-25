{{ config(materialized='table') }}

-- Collapses LSOA grain first, so the join below is month/crime_type ->
-- one row per force rather than fanning out across every LSOA.
with force_totals as (
    select
        month,
        crime_type,
        falls_within,
        sum(crimes) as falls_within_crimes
    from {{ ref('agg_crimes_by_lsoa_force_month_category') }}
    group by month, crime_type, falls_within
)

select
    amc.month,
    amc.crimes as total_crimes,
    coalesce(ft.falls_within, 'Censored') as falls_within,
    coalesce(ft.falls_within_crimes, 0) as falls_within_crimes,
    case
        when coalesce(ft.falls_within_crimes, 0) = 0 or amc.crimes = 0 then 0
        else ft.falls_within_crimes / amc.crimes
    end as crime_proportion,
    amc.crime_type
from {{ ref('agg_crimes_by_month_category') }} amc
left join force_totals ft
    on amc.month = ft.month
    and amc.crime_type = ft.crime_type
