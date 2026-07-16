-- BOM integrity mart: per parent assembly structure health.
{{ config(schema='marts', materialized='table') }}
select
    b.parent_part_key,
    count(*) as component_count,
    count(case when c.part_key is null then 1 end) as missing_components,
    count(case when c.lifecycle_status = 'OBSOLETE' then 1 end) as obsolete_components,
    count(case when c.lifecycle_status = 'BLOCKED' then 1 end) as blocked_components,
    count(case when b.quantity_per <= 0 then 1 end) as invalid_quantities,
    coalesce(max(bs.bom_quality_score), 100.0) as bom_quality_score
from {{ ref('fact_bom_relationship') }} b
left join {{ ref('dim_part') }} c on c.part_key = b.child_part_key
left join {{ source('quality', 'bom_scores') }} bs on bs.parent_part_key = b.parent_part_key
group by 1
