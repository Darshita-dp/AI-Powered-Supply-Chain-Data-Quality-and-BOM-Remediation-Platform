select
    plant_code as plant_key,
    plant_name,
    country,
    region,
    currency
from {{ source('raw', 'plants') }}
