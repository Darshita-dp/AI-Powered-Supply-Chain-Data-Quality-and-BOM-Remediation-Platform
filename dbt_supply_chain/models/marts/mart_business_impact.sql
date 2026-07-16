-- Business-impact mart: per part financial and demand exposure with issue flags.
{{ config(schema='marts', materialized='table') }}
select
    p.part_key,
    p.category,
    p.primary_plant,
    p.lifecycle_status,
    coalesce(inv.inventory_value, 0) as inventory_value,
    coalesce(dem.demand_qty, 0) as future_demand_qty,
    coalesce(po.po_value, 0) as open_po_value,
    coalesce(iss.open_issues, 0) as open_issues,
    coalesce(iss.critical_issues, 0) as critical_issues
from {{ ref('dim_part') }} p
left join (
    select part_key, sum(on_hand_value) as inventory_value
    from {{ ref('fact_inventory') }} group by 1
) inv on inv.part_key = p.part_key
left join (
    select part_key, sum(demand_qty) as demand_qty
    from {{ ref('fact_future_demand') }} group by 1
) dem on dem.part_key = p.part_key
left join (
    select part_key, sum(line_value) as po_value
    from {{ ref('fact_purchase_order') }} where status = 'OPEN' group by 1
) po on po.part_key = p.part_key
left join (
    select entity_key,
           count(*) as open_issues,
           count(case when severity = 'critical' then 1 end) as critical_issues
    from {{ source('quality', 'dq_issues') }}
    where status not in ('CLOSED', 'REJECTED') group by 1
) iss on iss.entity_key = p.part_key
