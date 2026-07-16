# Report Page Specifications — BOM Guardian AI

Seven pages, all using the theme in `../theme/bom-guardian-theme.json`. Wireframes are
described as visual layouts (top-left → bottom-right). Every visual lists its measures
from `../dax/measures.dax`.

Common elements on every page: slicer panel (left rail) with DimDate date range,
DimPlant plant, DimPart category; page header with page title and last-refresh card.

## 1. Executive Data Quality Command Center

| Zone | Visual | Fields / measures |
|---|---|---|
| KPI row (5 cards) | Card | [Enterprise Quality Score], [Open Issues], [Critical Open Issues], [Inventory Value Exposed], [Acceptance Rate] |
| Left, middle | Line chart "Issues detected over time" | DimDate[date_key] × [Issues Detected], legend severity |
| Right, middle | Stacked bar "Open issues by domain" | ExecutiveQuality[domain] × [Open Issues], legend severity |
| Bottom | Table "Top rules by open issues" | rule_id, rule_name, [Open Issues], [Critical Open Issues] |

Drill-through: rule_id → Part Master Quality filtered to that rule's issues.

## 2. Part Master Quality

- KPI cards: [Avg Part Quality Score], [Parts Below Quality Threshold]
- Histogram (clustered column over binned quality_score) of PartQuality
- Matrix: source_system × category with [Avg Part Quality Score] conditional formatting (bad < 60 red)
- Table: worst 50 parts (part_key, source_part_number, quality_score, open_issues, critical_issues)
- Tooltip page "Part tooltip": part attributes + issue counts (shown on hover of any part visual)

## 3. BOM Integrity

- KPI cards: [Avg BOM Quality Score], [Assemblies With Obsolete Components], [Assemblies With Missing Components]
- Scatter: component_count × bom_quality_score, size = obsolete_components
- Table: assemblies with structural defects (parent_part_key, component_count, missing/obsolete/blocked counts, invalid_quantities)

## 4. Supplier and Lead-Time Quality

- KPI cards: [Suppliers With Open Issues], [Avg Supplier Lead Time]
- Bar: top suppliers by open_issues_on_parts
- Scatter: parts_supplied × avg_lead_time_days, size = open_issues_on_parts
- Table: supplier detail with country/currency

## 5. Business Impact

- KPI cards: [Inventory Value Exposed], [Demand Qty Exposed], [Open PO Value Exposed], [Exposure % of Inventory]
- Treemap: category × [Inventory Value Exposed]
- Bar by plant: [Inventory Value Exposed] with [Parts With Critical Exposure] tooltip
- Table: top exposed parts

## 6. Remediation Performance

- KPI cards: [Decisions Made], [Acceptance Rate]
- Line: decisions over DimDate by decision type
- Bar: decisions by reviewer
- Matrix: severity × decision

## 7. AI Governance

- KPI cards: [AI Calls], [AI Abstention Rate], [AI Validation Failure Rate], [AI Avg Latency (ms)], [AI Avg Confidence]
- Line: [AI Calls] over call_date by provider
- Table: provider / model / prompt_version with all governance measures

## Drill-through and tooltip summary

- Drill-through targets: Part Master Quality (from any part_key), Business Impact
  (from plant), Remediation Performance (from rule_id).
- Tooltip pages: "Part tooltip" (page 2), "Supplier tooltip" (page 4).
