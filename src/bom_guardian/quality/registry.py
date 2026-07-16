"""The rule registry: 45 executable data-quality rules.

Rules run against the staging/core layers built by dbt. Each SQL returns one
row per violation with (entity_type, entity_key, field, failed_value); the
engine adds execution metadata and evidence.

Graph-integrity rules that need traversal (multi-hop cycles, depth) live in the
BOM graph module (M11) — the SQL rules here catch the directly-expressible cases.
"""

from __future__ import annotations

from bom_guardian.quality.models import Rule, RuleDomain, RuleSeverity

_C = RuleDomain.COMPLETENESS
_U = RuleDomain.UNIQUENESS
_V = RuleDomain.VALIDITY
_R = RuleDomain.REFERENTIAL
_X = RuleDomain.CONSISTENCY
_T = RuleDomain.TEMPORAL
_A = RuleDomain.ANOMALY
_G = RuleDomain.GRAPH
_D = RuleDomain.RECONCILIATION

CRIT = RuleSeverity.CRITICAL
HIGH = RuleSeverity.HIGH
MED = RuleSeverity.MEDIUM
LOW = RuleSeverity.LOW


def _part_null(field: str) -> str:
    return (
        "select 'part' as entity_type, part_key as entity_key, "
        f"'{field}' as field, null as failed_value "
        f"from core.dim_part where {field} is null"
    )


RULES: list[Rule] = [
    # ---------------- Completeness ----------------
    Rule(
        rule_id="COMP-001",
        name="Part missing description",
        severity=HIGH,
        domain=_C,
        description="Every part must carry a description.",
        sql=_part_null("description"),
        remediation_guidance="Source description from engineering or supplier data.",
    ),
    Rule(
        rule_id="COMP-002",
        name="Part missing category",
        severity=MED,
        domain=_C,
        description="Part category drives sourcing and reporting.",
        sql=_part_null("category"),
    ),
    Rule(
        rule_id="COMP-003",
        name="Part missing UOM",
        severity=CRIT,
        domain=_C,
        description="A part without a unit of measure blocks transactions.",
        sql=_part_null("uom"),
    ),
    Rule(
        rule_id="COMP-004",
        name="Purchased part missing supplier",
        severity=HIGH,
        domain=_C,
        description="BUY parts must have at least one supplier relationship.",
        sql="""
            select 'part', p.part_key, 'supplier', null
            from core.dim_part p
            left join staging.stg_supplier_parts sp on sp.part_id = p.part_key
            where p.procurement_type = 'BUY' and sp.part_id is null
         """,
    ),
    Rule(
        rule_id="COMP-005",
        name="Part missing lead time",
        severity=HIGH,
        domain=_C,
        description="Missing lead time breaks MRP.",
        sql=_part_null("lead_time_days"),
    ),
    Rule(
        rule_id="COMP-006",
        name="Part missing standard cost",
        severity=HIGH,
        domain=_C,
        description="Missing cost breaks valuation.",
        sql=_part_null("standard_cost"),
    ),
    Rule(
        rule_id="COMP-007",
        name="Part missing plant",
        severity=MED,
        domain=_C,
        description="Parts must belong to a primary plant.",
        sql=_part_null("primary_plant"),
    ),
    Rule(
        rule_id="COMP-008",
        name="Part missing manufacturer number",
        severity=LOW,
        domain=_C,
        description="MPN supports duplicate detection and sourcing.",
        sql=_part_null("manufacturer_part_number"),
    ),
    # ---------------- Uniqueness ----------------
    Rule(
        rule_id="UNIQ-001",
        name="Duplicate source part number in source system",
        severity=CRIT,
        domain=_U,
        description="Same source part number twice within one source system.",
        sql="""
            select 'part', part_key, 'source_part_number', source_part_number
            from core.dim_part
            where (source_part_number, source_system) in (
                select source_part_number, source_system from core.dim_part
                where source_part_number is not null
                group by 1, 2 having count(*) > 1)
         """,
    ),
    Rule(
        rule_id="UNIQ-002",
        name="Duplicate normalized part number across sources",
        severity=HIGH,
        domain=_U,
        description="Same normalized part number in more than one source record.",
        sql="""
            select 'part', part_key, 'part_number_normalized', part_number_normalized
            from core.dim_part
            where part_number_normalized in (
                select part_number_normalized from core.dim_part
                where part_number_normalized is not null and part_number_normalized != ''
                group by 1 having count(*) > 1)
         """,
    ),
    Rule(
        rule_id="UNIQ-003",
        name="Duplicate normalized supplier name",
        severity=CRIT,
        domain=_U,
        description="Same normalized supplier name registered more than once.",
        sql="""
            select 'supplier', supplier_key, 'supplier_name_normalized', supplier_name_normalized
            from core.dim_supplier
            where supplier_name_normalized in (
                select supplier_name_normalized from core.dim_supplier
                group by 1 having count(*) > 1)
         """,
    ),
    Rule(
        rule_id="UNIQ-004",
        name="Duplicate manufacturer part number",
        severity=HIGH,
        domain=_U,
        description="One MPN mapped to multiple internal parts.",
        sql="""
            select 'part', part_key, 'mpn_normalized', mpn_normalized
            from core.dim_part
            where mpn_normalized in (
                select mpn_normalized from core.dim_part
                where mpn_normalized is not null and mpn_normalized != ''
                group by 1 having count(*) > 1)
         """,
    ),
    Rule(
        rule_id="UNIQ-005",
        name="Multiple current revisions per BOM",
        severity=HIGH,
        domain=_U,
        description="A BOM header must have exactly one current revision.",
        sql="""
            select 'revision', revision_id, 'is_current', 'true'
            from staging.stg_engineering_revisions
            where is_current and bom_header_id in (
                select bom_header_id from staging.stg_engineering_revisions
                where is_current group by 1 having count(*) > 1)
         """,
    ),
    # ---------------- Validity ----------------
    Rule(
        rule_id="VALD-001",
        name="Invalid UOM code",
        severity=HIGH,
        domain=_V,
        description="UOM must exist in the governed UOM reference.",
        sql="""
            select 'part', p.part_key, 'uom', p.uom
            from core.dim_part p
            where p.uom is not null and p.uom not in (select uom_code from raw.units_of_measure)
         """,
    ),
    Rule(
        rule_id="VALD-002",
        name="Invalid currency code",
        severity=HIGH,
        domain=_V,
        description="Currency must be an ISO code used by the business.",
        sql="""
            select 'supplier_part', supplier_part_id, 'currency', currency
            from staging.stg_supplier_parts
            where currency not in ('USD','EUR','GBP','INR','CNY','MXN')
         """,
    ),
    Rule(
        rule_id="VALD-003",
        name="Invalid lifecycle status",
        severity=MED,
        domain=_V,
        description="Lifecycle status outside the governed set.",
        sql="""
            select 'part', part_key, 'lifecycle_status', lifecycle_status
            from core.dim_part
            where lifecycle_status is not null
              and lifecycle_status not in ('ACTIVE','BLOCKED','OBSOLETE','IN_DEVELOPMENT')
         """,
    ),
    Rule(
        rule_id="VALD-004",
        name="Non-positive standard cost",
        severity=HIGH,
        domain=_V,
        description="Standard cost must be positive.",
        sql="""
            select 'part', part_key, 'standard_cost', cast(standard_cost as varchar)
            from core.dim_part where standard_cost <= 0
         """,
    ),
    Rule(
        rule_id="VALD-005",
        name="Negative lead time",
        severity=HIGH,
        domain=_V,
        description="Lead time cannot be negative.",
        sql="""
            select 'part', part_key, 'lead_time_days', cast(lead_time_days as varchar)
            from core.dim_part where lead_time_days < 0
         """,
    ),
    Rule(
        rule_id="VALD-006",
        name="Zero BOM component quantity",
        severity=CRIT,
        domain=_V,
        description="BOM quantity of zero produces nothing.",
        sql="""
            select 'bom_relationship', bom_rel_key, 'quantity_per', cast(quantity_per as varchar)
            from core.fact_bom_relationship where quantity_per = 0
         """,
    ),
    Rule(
        rule_id="VALD-007",
        name="Negative BOM component quantity",
        severity=CRIT,
        domain=_V,
        description="Negative BOM quantities are invalid.",
        sql="""
            select 'bom_relationship', bom_rel_key, 'quantity_per', cast(quantity_per as varchar)
            from core.fact_bom_relationship where quantity_per < 0
         """,
    ),
    Rule(
        rule_id="VALD-008",
        name="Revision end date before start date",
        severity=HIGH,
        domain=_V,
        description="Effectivity window must be ordered.",
        sql="""
            select 'revision', revision_id, 'effective_to', cast(effective_to as varchar)
            from staging.stg_engineering_revisions
            where effective_to is not null and effective_to < effective_from
         """,
    ),
    # ---------------- Referential integrity ----------------
    Rule(
        rule_id="REFI-001",
        name="BOM parent not in part master",
        severity=CRIT,
        domain=_R,
        description="Every BOM parent must exist as a part.",
        sql="""
            select 'bom_relationship', b.bom_rel_key, 'parent_part_key', b.parent_part_key
            from core.fact_bom_relationship b
            left join core.dim_part p on p.part_key = b.parent_part_key
            where p.part_key is null
         """,
    ),
    Rule(
        rule_id="REFI-002",
        name="BOM child not in part master",
        severity=CRIT,
        domain=_R,
        description="Every BOM component must exist as a part.",
        sql="""
            select 'bom_relationship', b.bom_rel_key, 'child_part_key', b.child_part_key
            from core.fact_bom_relationship b
            left join core.dim_part p on p.part_key = b.child_part_key
            where p.part_key is null
         """,
    ),
    Rule(
        rule_id="REFI-003",
        name="Supplier-part references missing supplier",
        severity=HIGH,
        domain=_R,
        description="Supplier relationship must point at a registered supplier.",
        sql="""
            select 'supplier_part', sp.supplier_part_id, 'supplier_id', sp.supplier_id
            from staging.stg_supplier_parts sp
            left join core.dim_supplier s on s.supplier_key = sp.supplier_id
            where s.supplier_key is null
         """,
    ),
    Rule(
        rule_id="REFI-004",
        name="Part references missing plant",
        severity=HIGH,
        domain=_R,
        description="primary_plant must exist in the plant dimension.",
        sql="""
            select 'part', p.part_key, 'primary_plant', p.primary_plant
            from core.dim_part p
            left join core.dim_plant pl on pl.plant_key = p.primary_plant
            where p.primary_plant is not null and pl.plant_key is null
         """,
    ),
    Rule(
        rule_id="REFI-005",
        name="Future demand references missing part",
        severity=HIGH,
        domain=_R,
        description="Demand must reference an existing part.",
        sql="""
            select 'demand', d.demand_key, 'part_key', d.part_key
            from core.fact_future_demand d
            left join core.dim_part p on p.part_key = d.part_key
            where p.part_key is null
         """,
    ),
    Rule(
        rule_id="REFI-006",
        name="Cost history references missing part",
        severity=MED,
        domain=_R,
        description="Cost history must reference an existing part.",
        sql="""
            select 'cost', c.cost_key, 'part_key', c.part_key
            from core.fact_standard_cost c
            left join core.dim_part p on p.part_key = c.part_key
            where p.part_key is null
         """,
    ),
    # ---------------- Cross-field consistency ----------------
    Rule(
        rule_id="XFLD-001",
        name="Manufactured part without BOM",
        severity=HIGH,
        domain=_X,
        description="MAKE parts should have a bill of materials.",
        sql="""
            select 'part', p.part_key, 'bom', null
            from core.dim_part p
            left join core.fact_bom_relationship b on b.parent_part_key = p.part_key
            where p.procurement_type = 'MAKE' and p.bom_tier >= 2 and b.parent_part_key is null
         """,
    ),
    Rule(
        rule_id="XFLD-002",
        name="Obsolete part with future demand",
        severity=CRIT,
        domain=_X,
        description="Obsolete parts must not carry future demand.",
        sql="""
            select 'part', p.part_key, 'lifecycle_status', p.lifecycle_status
            from core.dim_part p
            join core.fact_future_demand d on d.part_key = p.part_key
            where p.lifecycle_status = 'OBSOLETE'
            group by 1, 2, 3, 4
         """,
    ),
    Rule(
        rule_id="XFLD-003",
        name="Blocked part with future demand",
        severity=CRIT,
        domain=_X,
        description="Blocked parts with open demand will fail MRP.",
        sql="""
            select 'part', p.part_key, 'lifecycle_status', p.lifecycle_status
            from core.dim_part p
            join core.fact_future_demand d on d.part_key = p.part_key
            where p.lifecycle_status = 'BLOCKED'
            group by 1, 2, 3, 4
         """,
    ),
    Rule(
        rule_id="XFLD-004",
        name="Obsolete component in active BOM",
        severity=CRIT,
        domain=_X,
        description="Active assemblies must not consume obsolete components.",
        sql="""
            select 'bom_relationship', b.bom_rel_key, 'child_lifecycle', c.lifecycle_status
            from core.fact_bom_relationship b
            join core.dim_part c on c.part_key = b.child_part_key
            join core.dim_part par on par.part_key = b.parent_part_key
            where c.lifecycle_status = 'OBSOLETE' and par.lifecycle_status = 'ACTIVE'
         """,
    ),
    Rule(
        rule_id="XFLD-005",
        name="Blocked component in active BOM",
        severity=HIGH,
        domain=_X,
        description="Blocked components inside active assemblies stall production.",
        sql="""
            select 'bom_relationship', b.bom_rel_key, 'child_lifecycle', c.lifecycle_status
            from core.fact_bom_relationship b
            join core.dim_part c on c.part_key = b.child_part_key
            join core.dim_part par on par.part_key = b.parent_part_key
            where c.lifecycle_status = 'BLOCKED' and par.lifecycle_status = 'ACTIVE'
         """,
    ),
    Rule(
        rule_id="XFLD-006",
        name="Supplier currency mismatch",
        severity=MED,
        domain=_X,
        description="Supplier-part currency should match the supplier's default currency.",
        sql="""
            select 'supplier_part', sp.supplier_part_id, 'currency', sp.currency
            from staging.stg_supplier_parts sp
            join core.dim_supplier s on s.supplier_key = sp.supplier_id
            where sp.currency != s.currency and sp.currency != 'USD'
         """,
    ),
    Rule(
        rule_id="XFLD-007",
        name="Category/UOM mismatch",
        severity=LOW,
        domain=_X,
        description="Raw materials are weight/length UOMs; discrete categories are EA/SET.",
        sql="""
            select 'part', part_key, 'uom', uom
            from core.dim_part
            where category = 'RAW_MATERIALS' and uom in ('EA','SET','PR')
         """,
    ),
    # ---------------- Temporal consistency ----------------
    Rule(
        rule_id="TEMP-001",
        name="Overlapping revision effectivity",
        severity=HIGH,
        domain=_T,
        description="Revision windows for a BOM must not overlap.",
        sql="""
            select 'revision', a.revision_id, 'effective_to', cast(a.effective_to as varchar)
            from staging.stg_engineering_revisions a
            join staging.stg_engineering_revisions b
              on a.bom_header_id = b.bom_header_id and a.revision_id < b.revision_id
            where a.effective_to is not null
              and a.effective_from <= coalesce(b.effective_to, date '2999-12-31')
              and b.effective_from <= a.effective_to
         """,
    ),
    Rule(
        rule_id="TEMP-002",
        name="Stale active part record",
        severity=MED,
        domain=_T,
        threshold=1095.0,
        description="Active parts untouched for 3+ years are governance risks.",
        sql="""
            select 'part', part_key, 'last_updated', cast(last_updated as varchar)
            from core.dim_part
            where lifecycle_status = 'ACTIVE'
              and last_updated < date '2026-07-01' - interval 1095 day
         """,
    ),
    Rule(
        rule_id="TEMP-003",
        name="Cost effectivity in the future beyond horizon",
        severity=LOW,
        domain=_T,
        description="Cost records effective far in the future are suspect.",
        sql="""
            select 'cost', cost_key, 'effective_from', cast(effective_from as varchar)
            from core.fact_standard_cost
            where effective_from > date '2026-07-01' + interval 365 day
         """,
    ),
    Rule(
        rule_id="TEMP-004",
        name="Part updated before created",
        severity=HIGH,
        domain=_T,
        description="last_updated must not precede created_date.",
        sql="""
            select 'part', part_key, 'last_updated', cast(last_updated as varchar)
            from core.dim_part where last_updated < created_date
         """,
    ),
    # ---------------- Anomalies ----------------
    Rule(
        rule_id="ANOM-001",
        name="Extreme standard-cost movement",
        severity=HIGH,
        domain=_A,
        threshold=4.0,
        description="Latest cost more than 4x away from the previous record.",
        sql="""
            with ranked as (
                select part_key, standard_cost, effective_from,
                       lag(standard_cost) over (partition by part_key order by effective_from)
                           as prev_cost,
                       cost_key
                from core.fact_standard_cost
            )
            select 'cost', cost_key, 'standard_cost',
                   cast(standard_cost as varchar) || ' (prev ' || cast(prev_cost as varchar) || ')'
            from ranked
            where prev_cost is not null and prev_cost > 0
              and (standard_cost / prev_cost > 4.0 or standard_cost / prev_cost < 0.25)
         """,
    ),
    Rule(
        rule_id="ANOM-002",
        name="Extreme lead-time movement",
        severity=HIGH,
        domain=_A,
        threshold=3.0,
        description="Latest lead time more than 3x the prior value.",
        sql="""
            with ranked as (
                select lead_time_key, part_key, lead_time_days, effective_from,
                       lag(lead_time_days) over (partition by part_key, supplier_key
                                                 order by effective_from) as prev_lt
                from core.fact_lead_time
            )
            select 'lead_time', lead_time_key, 'lead_time_days',
                   cast(lead_time_days as varchar) || ' (prev ' || cast(prev_lt as varchar) || ')'
            from ranked
            where prev_lt is not null and prev_lt > 0 and lead_time_days > prev_lt * 3
         """,
    ),
    Rule(
        rule_id="ANOM-003",
        name="Negative inventory",
        severity=HIGH,
        domain=_A,
        description="On-hand quantity below zero.",
        sql="""
            select 'inventory', inventory_key, 'on_hand_qty', cast(on_hand_qty as varchar)
            from core.fact_inventory where on_hand_qty < 0
         """,
    ),
    Rule(
        rule_id="ANOM-004",
        name="Supplier price divergence for one part",
        severity=MED,
        domain=_A,
        threshold=2.5,
        description="A supplier price more than 2.5x the minimum price for the same part.",
        sql="""
            with spread as (
                select part_id, min(unit_price) as min_price
                from staging.stg_supplier_parts
                where unit_price > 0 group by 1 having count(*) > 1
            )
            select 'supplier_part', sp.supplier_part_id, 'unit_price',
                   cast(sp.unit_price as varchar) || ' (min ' || cast(s.min_price as varchar) || ')'
            from staging.stg_supplier_parts sp
            join spread s on s.part_id = sp.part_id
            where sp.unit_price > s.min_price * 2.5
         """,
    ),
    Rule(
        rule_id="ANOM-005",
        name="Extreme BOM component quantity",
        severity=MED,
        domain=_A,
        threshold=100.0,
        description="Quantity-per above 100 is out of range for this product family.",
        sql="""
            select 'bom_relationship', bom_rel_key, 'quantity_per', cast(quantity_per as varchar)
            from core.fact_bom_relationship where quantity_per > 100
         """,
    ),
    # ---------------- Graph integrity (SQL-expressible subset) ----------------
    Rule(
        rule_id="GRPH-001",
        name="Self-referencing BOM",
        severity=CRIT,
        domain=_G,
        description="A part cannot be its own component.",
        sql="""
            select 'bom_relationship', bom_rel_key, 'child_part_key', child_part_key
            from core.fact_bom_relationship where parent_part_key = child_part_key
         """,
    ),
    Rule(
        rule_id="GRPH-002",
        name="Direct two-node BOM cycle",
        severity=CRIT,
        domain=_G,
        description="A is a component of B while B is a component of A.",
        sql="""
            select 'bom_relationship', a.bom_rel_key, 'cycle',
                   a.parent_part_key || '<->' || a.child_part_key
            from core.fact_bom_relationship a
            join core.fact_bom_relationship b
              on a.parent_part_key = b.child_part_key
             and a.child_part_key = b.parent_part_key
             and a.parent_part_key != a.child_part_key
         """,
    ),
    Rule(
        rule_id="GRPH-003",
        name="Duplicate component position in BOM",
        severity=LOW,
        domain=_G,
        description="Same child appears twice under one parent and revision.",
        sql="""
            select 'bom_relationship', bom_rel_key, 'child_part_key', child_part_key
            from core.fact_bom_relationship
            where (parent_part_key, child_part_key, revision_label) in (
                select parent_part_key, child_part_key, revision_label
                from core.fact_bom_relationship
                group by 1, 2, 3 having count(*) > 1)
         """,
    ),
    # ---------------- Document / ERP reconciliation ----------------
    Rule(
        rule_id="DOCR-001",
        name="Quote price conflicts with ERP price",
        severity=HIGH,
        domain=_D,
        threshold=1.30,
        description="Supplier quote differs from the ERP supplier-part price by >30%.",
        sql="""
            select 'quote', q.quote_id, 'quoted_price',
                   cast(q.quoted_price as varchar)
                       || ' (erp ' || cast(sp.unit_price as varchar) || ')'
            from raw.supplier_quotes q
            join staging.stg_supplier_parts sp
              on sp.supplier_id = q.supplier_id and sp.part_id = q.part_id
            where sp.unit_price > 0
              and (q.quoted_price / sp.unit_price > 1.30 or q.quoted_price / sp.unit_price < 0.70)
         """,
    ),
    Rule(
        rule_id="DOCR-002",
        name="Quote lead time conflicts with ERP",
        severity=HIGH,
        domain=_D,
        threshold=14.0,
        description="Quoted lead time differs from ERP by more than 14 days.",
        sql="""
            select 'quote', q.quote_id, 'quoted_lead_time_days',
                   cast(q.quoted_lead_time_days as varchar)
                   || ' (erp ' || cast(sp.lead_time_days as varchar) || ')'
            from raw.supplier_quotes q
            join staging.stg_supplier_parts sp
              on sp.supplier_id = q.supplier_id and sp.part_id = q.part_id
            where abs(q.quoted_lead_time_days - sp.lead_time_days) > 14
         """,
    ),
    Rule(
        rule_id="DOCR-003",
        name="Expired quote still in force",
        severity=LOW,
        domain=_D,
        description="Quotes past their valid_to date should be archived.",
        sql="""
            select 'quote', quote_id, 'valid_to', cast(valid_to as varchar)
            from raw.supplier_quotes
            where cast(valid_to as date) < date '2026-07-01' - interval 90 day
         """,
    ),
]


def enabled_rules() -> list[Rule]:
    return [r for r in RULES if r.enabled]
