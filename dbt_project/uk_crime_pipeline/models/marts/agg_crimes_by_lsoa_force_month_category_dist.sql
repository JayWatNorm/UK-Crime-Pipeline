{{ config(materialized='table') }}
WITH force_totals AS (
    SELECT
        month,
        crime_type,
        falls_within,
        SUM(crimes) AS falls_within_crimes
    FROM {{ ref('agg_crimes_by_lsoa_force_month_category') }}
    GROUP BY month, crime_type, falls_within
)
SELECT
    AMC.month,
    AMC.crimes AS total_crimes,
    COALESCE(FT.falls_within, 'Censored') AS falls_within,
    COALESCE(FT.falls_within_crimes, 0) AS falls_within_crimes,
    CASE WHEN COALESCE(FT.falls_within_crimes, 0) = 0 OR AMC.crimes = 0 THEN 0
         ELSE FT.falls_within_crimes / AMC.crimes END AS crime_proportion,
    AMC.crime_type
FROM {{ ref('agg_crimes_by_month_category') }} AMC
LEFT JOIN force_totals FT ON AMC.month = FT.month AND AMC.crime_type = FT.crime_type
