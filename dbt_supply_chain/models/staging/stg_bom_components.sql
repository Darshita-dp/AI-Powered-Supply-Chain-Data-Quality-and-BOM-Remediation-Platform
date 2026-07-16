select
    bom_component_id,
    bom_header_id,
    parent_part_id,
    child_part_id,
    try_cast(quantity_per as decimal(18, 4)) as quantity_per,
    upper(trim(uom)) as uom,
    revision_label,
    try_cast(effective_from as date) as effective_from,
    try_cast(effective_to as date) as effective_to,
    try_cast(position as integer) as position,
    _ingestion_batch_id,
    _row_hash
from {{ source('raw', 'bom_components') }}
