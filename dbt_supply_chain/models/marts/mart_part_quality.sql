-- Part-master quality mart: per-part issue counts, score, and attributes.
{{ config(schema='marts', materialized='table') }}
select
    p.part_key,
    p.source_part_number,
    p.source_system,
    p.category,
    p.lifecycle_status,
    p.primary_plant,
    coalesce(es.quality_score, 100.0) as quality_score,
    count(i.issue_id) as open_issues,
    count(case when i.severity = 'critical' then 1 end) as critical_issues
from {{ ref('dim_part') }} p
left join {{ source('quality', 'entity_scores') }} es
    on es.entity_key = p.part_key and es.entity_type = 'part'
left join {{ source('quality', 'dq_issues') }} i
    on i.entity_key = p.part_key and i.status not in ('CLOSED', 'REJECTED')
group by 1, 2, 3, 4, 5, 6, 7
