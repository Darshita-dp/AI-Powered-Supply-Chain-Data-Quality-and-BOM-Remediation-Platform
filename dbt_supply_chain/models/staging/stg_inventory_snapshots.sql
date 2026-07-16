select
    inventory_id,
    part_id,
    upper(trim(warehouse_code)) as warehouse_code,
    try_cast(snapshot_date as date) as snapshot_date,
    try_cast(on_hand_qty as decimal(18, 2)) as on_hand_qty,
    try_cast(on_hand_value as decimal(18, 2)) as on_hand_value,
    try_cast(safety_stock_qty as decimal(18, 2)) as safety_stock_qty,
    _ingestion_batch_id,
    _row_hash
from {{ source('raw', 'inventory_snapshots') }}
