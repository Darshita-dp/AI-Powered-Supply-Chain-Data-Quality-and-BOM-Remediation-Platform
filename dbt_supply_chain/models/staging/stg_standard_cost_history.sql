select
    cost_history_id,
    part_id,
    upper(trim(plant_code)) as plant_code,
    try_cast(standard_cost as decimal(18, 4)) as standard_cost,
    upper(trim(currency)) as currency,
    try_cast(effective_from as date) as effective_from,
    _ingestion_batch_id,
    _row_hash
from {{ source('raw', 'standard_cost_history') }}
