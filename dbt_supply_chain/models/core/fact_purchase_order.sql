select
    po_line_id as po_line_key,
    po_id,
    line_number,
    part_id as part_key,
    supplier_id as supplier_key,
    plant_code as plant_key,
    order_date,
    currency,
    status,
    order_qty,
    unit_price,
    line_value,
    promised_date
from {{ ref('stg_purchase_order_lines') }}
