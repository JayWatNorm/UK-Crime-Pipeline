{{ config(materialized='table') }}


WITH last_recorded_year AS (
    SELECT *
    FROM {{ ref('agg_crimes_by_lsoa_latlong_month') }} ag
    WHERE lsoa_code IS NOT NULL
      AND EXTRACT(YEAR FROM ag.month) = (
          SELECT max(EXTRACT(YEAR FROM ag2.month))
          FROM {{ ref('agg_crimes_by_lsoa_latlong_month') }} ag2
      )
)

SELECT
    cy.lsoa_code,
    cy.month,
    cy.crimes AS cy_crimes,
    ly.crimes AS ly_crimes,
    cy.crimes - ly.crimes AS crime_change,
    round((cy.crimes - ly.crimes)::numeric / NULLIF(ly.crimes, 0), 4) AS crime_change_pct,
    cy.longitude,
    cy.latitude
FROM last_recorded_year cy
LEFT JOIN {{ ref('agg_crimes_by_lsoa_latlong_month') }} ly
    ON ly.lsoa_code = cy.lsoa_code
    AND ly.month = cy.month - interval '1 year'