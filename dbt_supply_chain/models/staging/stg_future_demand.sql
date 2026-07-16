select
    demand_id,
    part_id,
    upper(trim(plant_code)) as plant_code,
    try_cast(demand_date as date) as demand_date,
    try_cast(demand_qty as decimal(18, 2)) as demand_qty,
    upper(trim(demand_type)) as demand_type,
    _ingestion_batch_id,
    _row_hash
from {{ source('raw', 'future_demand') }}
