-- Standardized parts. Original values preserved; normalized companions added.
select
    part_id,
    source_part_number,
    {{ norm_part_number('source_part_number') }} as part_number_normalized,
    source_system,
    description,
    {{ norm_whitespace('upper(description)') }} as description_normalized,
    upper(trim(category)) as category,
    upper(trim(uom)) as uom,
    upper(trim(lifecycle_status)) as lifecycle_status,
    upper(trim(procurement_type)) as procurement_type,
    manufacturer_part_number,
    {{ norm_part_number('manufacturer_part_number') }} as mpn_normalized,
    try_cast(standard_cost as decimal(18, 4)) as standard_cost,
    upper(trim(currency)) as currency,
    try_cast(lead_time_days as integer) as lead_time_days,
    upper(trim(primary_plant)) as primary_plant,
    try_cast(bom_tier as integer) as bom_tier,
    try_cast(created_date as date) as created_date,
    try_cast(last_updated as date) as last_updated,
    _ingestion_batch_id,
    _row_hash
from {{ source('raw', 'part_master') }}
