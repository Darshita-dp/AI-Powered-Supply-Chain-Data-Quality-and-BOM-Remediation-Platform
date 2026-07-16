select
    revision_id,
    bom_header_id,
    part_id,
    upper(trim(revision_label)) as revision_label,
    try_cast(effective_from as date) as effective_from,
    try_cast(effective_to as date) as effective_to,
    try_cast(is_current as boolean) as is_current,
    _ingestion_batch_id,
    _row_hash
from {{ source('raw', 'engineering_revisions') }}
