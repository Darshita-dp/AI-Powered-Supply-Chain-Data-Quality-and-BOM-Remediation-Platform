select
    inventory_id as inventory_key,
    part_id as part_key,
    warehouse_code as warehouse_key,
    snapshot_date,
    on_hand_qty,
    on_hand_value,
    safety_stock_qty
from {{ ref('stg_inventory_snapshots') }}
