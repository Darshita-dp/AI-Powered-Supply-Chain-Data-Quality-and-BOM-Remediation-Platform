select
    lead_time_history_id as lead_time_key,
    part_id as part_key,
    supplier_id as supplier_key,
    lead_time_days,
    effective_from
from {{ ref('stg_lead_time_history') }}
