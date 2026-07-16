-- Executive quality mart: one row per rule/severity/domain/status combination.
{{ config(schema='marts', materialized='table') }}
select
    i.rule_id,
    r.name as rule_name,
    i.severity,
    i.domain,
    i.status,
    cast(i.detected_at as date) as detected_date,
    count(*) as issue_count
from {{ source('quality', 'dq_issues') }} i
left join {{ source('quality', 'dq_rules') }} r on r.rule_id = i.rule_id
group by 1, 2, 3, 4, 5, 6
