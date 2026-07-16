select
    bom_component_id as bom_rel_key,
    bom_header_id,
    parent_part_id as parent_part_key,
    child_part_id as child_part_key,
    quantity_per,
    uom,
    revision_label,
    effective_from,
    effective_to,
    position
from {{ ref('stg_bom_components') }}
