-- Remediation-performance mart: reviewer decisions over time.
{{ config(schema='marts', materialized='table') }}
select
    cast(d.decided_at as date) as decision_date,
    d.decision,
    d.reviewer,
    i.severity,
    i.domain,
    count(*) as decisions
from {{ source('quality', 'remediation_decisions') }} d
left join {{ source('quality', 'dq_issues') }} i on i.issue_id = d.issue_id
group by 1, 2, 3, 4, 5
