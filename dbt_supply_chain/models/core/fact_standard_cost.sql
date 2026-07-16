select
    cost_history_id as cost_key,
    part_id as part_key,
    plant_code as plant_key,
    standard_cost,
    currency,
    effective_from
from {{ ref('stg_standard_cost_history') }}
