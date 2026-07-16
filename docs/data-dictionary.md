# Data Dictionary — BOM Guardian AI

Column-level detail lives in the dbt models (`dbt_supply_chain/models/`) and generator
code (`data_generator/generators/`); this dictionary describes each dataset's grain and
purpose per layer.

## Raw layer (22 generator extracts + audit columns)

Every raw table additionally carries: `_ingestion_batch_id`, `_ingested_at`,
`_file_hash`, `_row_hash`, `_schema_version`, `_record_seq`, `_load_status`,
`_source_system_file`.

| Table | Grain | Notes |
|---|---|---|
| part_master | source part record | part number, description, category, UOM, lifecycle, MPN, cost, lead time, plant, source system |
| part_aliases | alias per part | cross-reference/customer/legacy part numbers |
| suppliers | supplier record | name, country, currency, terms, status, source system |
| supplier_parts | supplier × part | price, lead time, MOQ, primary flag |
| plants / warehouses | site | region, currency; warehouses link to plants |
| units_of_measure / product_categories | reference row | governed vocabularies |
| bom_headers | BOM per assembly × plant | usage, status |
| bom_components | parent × child edge | quantity-per, UOM, revision, effectivity, position |
| engineering_revisions | revision per BOM | label, effectivity window, is_current |
| engineering_change_orders | ECO | change type, status |
| part_substitutions / part_supersessions | relationship | substitute / replaced-by |
| inventory_snapshots | part × warehouse × date | qty, value, safety stock |
| purchase_orders / purchase_order_lines | PO / line | supplier, plant, qty, price, promised date |
| future_demand | part × plant × date | forecast/sales-order quantity |
| production_orders | order | assembly, plant, qty, dates, status |
| standard_cost_history / lead_time_history | temporal record | effectivity-dated values |
| supplier_quotes | quote | doc-comparable price/lead-time/validity |

## Staging (10 views) and Core (11 tables)

Staging normalizes casing/whitespace/part numbers/dates/types **without destroying
originals** (normalized companions added). Core conforms to a star schema:
`dim_part`, `dim_supplier`, `dim_plant`, `dim_warehouse`, `dim_date`,
`fact_bom_relationship`, `fact_inventory`, `fact_future_demand`,
`fact_purchase_order`, `fact_standard_cost`, `fact_lead_time`.
ER diagram: [diagrams/erd.md](diagrams/erd.md).

## Quality layer

| Table | Purpose |
|---|---|
| dq_rules | registry snapshot (49 rules, versioned, with remediation guidance) |
| dq_rule_executions | one row per rule per run (violations, duration, status) |
| dq_issues | one row per violation (entity, severity, domain, lifecycle status) |
| dq_issue_evidence | failed value + field per issue |
| entity_scores / bom_scores / enterprise_score | transparent quality scoring |
| remediation_decisions | human decision audit (reviewer, reason, before/after status) |
| ai_call_audit | AI governance record per provider call |
| scenarios | persisted counterfactual simulations (never touches core) |

## Ground truth (isolated)

`ground_truth.labels`: injection ID, issue type, affected record, field,
original/injected/correct values, matching entity, difficulty, seed, timestamp.
**Evaluation-only** — never joined into model inputs (ADR-004).

## Marts (7)

One table per analytics surface: executive quality, part quality, BOM integrity,
supplier quality, business impact, remediation performance, AI governance — specified
for Power BI in [../powerbi/semantic-model/model-specification.md](../powerbi/semantic-model/model-specification.md).
