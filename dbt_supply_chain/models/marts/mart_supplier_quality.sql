-- Supplier and lead-time quality mart.
{{ config(schema='marts', materialized='table') }}
with supplied as (
    select sp.supplier_id, sp.part_id, sp.unit_price, sp.lead_time_days
    from {{ ref('stg_supplier_parts') }} sp
)
select
    s.supplier_key,
    s.supplier_name,
    s.country,
    s.currency,
    count(distinct sp.part_id) as parts_supplied,
    avg(sp.lead_time_days) as avg_lead_time_days,
    count(distinct i.issue_id) as open_issues_on_parts
from {{ ref('dim_supplier') }} s
left join supplied sp on sp.supplier_id = s.supplier_key
left join {{ source('quality', 'dq_issues') }} i
    on i.entity_key = sp.part_id and i.status not in ('CLOSED', 'REJECTED')
group by 1, 2, 3, 4
