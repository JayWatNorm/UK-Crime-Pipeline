select
    id,
    (month || '-01')::date as month,
    (date::timestamptz)::date as search_date,
    (date::timestamptz)::time as search_time,
    type,
    part_of_policing_operation::boolean as part_of_policing_operation,
    longitude,
    latitude,
    gender,
    age_range,
    self_defined_ethnicity,
    officer_defined_ethnicity,
    legislation,
    object_of_search,
    outcome,
    outcome_linked_to_object_of_search::boolean as outcome_linked_to_object_of_search,
    removal_of_more_than_outer_clothing::boolean as removal_of_more_than_outer_clothing
from {{ source('raw', 'raw_stop_and_search') }}