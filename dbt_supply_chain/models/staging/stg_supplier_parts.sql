select
    supplier_part_id,
    supplier_id,
    part_id,
    supplier_part_number,
    {{ norm_part_number('supplier_part_number') }} as supplier_part_number_normalized,
    try_cast(unit_price as decimal(18, 4)) as unit_price,
    upper(trim(currency)) as currency,
    try_cast(lead_time_days as integer) as lead_time_days,
    try_cast(min_order_qty as integer) as min_order_qty,
    try_cast(is_primary as boolean) as is_primary,
    _ingestion_batch_id,
    _row_hash
from {{ source('raw', 'supplier_parts') }}
