{{ config(materialized='table') }}

select
    id,
    month,
    search_date,
    search_time,
    type,
    part_of_policing_operation,
    longitude,
    latitude,
    gender,
    age_range,
    self_defined_ethnicity,
    officer_defined_ethnicity,
    legislation,
    object_of_search,
    outcome,
    outcome_linked_to_object_of_search,
    removal_of_more_than_outer_clothing
from {{ ref('stg_stop_and_search') }}
