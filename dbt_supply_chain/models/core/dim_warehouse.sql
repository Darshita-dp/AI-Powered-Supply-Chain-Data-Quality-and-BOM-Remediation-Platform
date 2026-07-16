select
    warehouse_code as warehouse_key,
    warehouse_name,
    plant_code as plant_key
from {{ source('raw', 'warehouses') }}
