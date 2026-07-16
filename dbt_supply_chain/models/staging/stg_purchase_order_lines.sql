select
    l.po_line_id,
    l.po_id,
    try_cast(l.line_number as integer) as line_number,
    l.part_id,
    h.supplier_id,
    upper(trim(h.plant_code)) as plant_code,
    try_cast(h.order_date as date) as order_date,
    upper(trim(h.currency)) as currency,
    upper(trim(h.status)) as status,
    try_cast(l.order_qty as decimal(18, 2)) as order_qty,
    try_cast(l.unit_price as decimal(18, 4)) as unit_price,
    try_cast(l.line_value as decimal(18, 2)) as line_value,
    try_cast(l.promised_date as date) as promised_date,
    l._ingestion_batch_id,
    l._row_hash
from {{ source('raw', 'purchase_order_lines') }} l
left join {{ source('raw', 'purchase_orders') }} h on l.po_id = h.po_id
