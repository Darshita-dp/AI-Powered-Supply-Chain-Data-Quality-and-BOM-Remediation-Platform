select
    demand_id as demand_key,
    part_id as part_key,
    plant_code as plant_key,
    demand_date,
    demand_qty,
    demand_type
from {{ ref('stg_future_demand') }}
