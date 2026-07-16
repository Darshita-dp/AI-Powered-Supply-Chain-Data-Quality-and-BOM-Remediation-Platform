select
    lead_time_history_id,
    part_id,
    supplier_id,
    try_cast(lead_time_days as integer) as lead_time_days,
    try_cast(effective_from as date) as effective_from,
    _ingestion_batch_id,
    _row_hash
from {{ source('raw', 'lead_time_history') }}
