{{ config(materialized='table') }}

WITH date_range AS (
    SELECT
        min(month) AS first_month,
        max(month) AS last_month
    FROM {{ ref('agg_crimes_by_lsoa_monthly_vs_prior_year') }}

),

ytd AS (
    SELECT
        lsoa_code,
        sum(cy_crimes) AS cy_crimes,
        sum(ly_crimes) AS ly_crimes,
        sum(cy_crimes) - sum(ly_crimes) AS crime_change,
        round((sum(cy_crimes) - sum(ly_crimes))::numeric / NULLIF(sum(ly_crimes), 0), 4) AS crime_change_pct,
        round(avg(longitude), 4) AS longitude,
        round(avg(latitude), 4) AS latitude
    FROM {{ ref('agg_crimes_by_lsoa_monthly_vs_prior_year') }}

    GROUP BY lsoa_code
)

SELECT
    ytd.lsoa_code,
    ytd.cy_crimes,
    ytd.ly_crimes,
    ytd.crime_change,
    ytd.crime_change_pct,
    ytd.longitude,
    ytd.latitude,
    concat(
        to_char(dr.first_month, 'YYYY-MM'), ' - ', to_char(dr.last_month, 'YYYY-MM'),
        ' vs ',
        to_char(dr.first_month - interval '1 year', 'YYYY-MM'), ' - ',
        to_char(dr.last_month - interval '1 year', 'YYYY-MM')
    ) AS comparison_period
FROM ytd
CROSS JOIN date_range dr