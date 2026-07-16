# Semantic Model Specification — BOM Guardian AI

**Status: source package only.** Power BI Desktop was not operated in this build
environment, so no `.pbix`/PBIP has been created or visually validated. Everything
needed to build the model is specified here; see `../BUILD_POWER_BI.md`.

## Source

- **Primary:** Snowflake `BOM_GUARDIAN.MARTS` (see connection instructions in BUILD doc)
- **Local fallback:** CSV extracts produced by `python scripts/export_powerbi_data.py`
  (one CSV per table below, from the local DuckDB warehouse)

## Tables (import mode)

| Table | Grain | Source object |
|---|---|---|
| ExecutiveQuality | rule × severity × domain × status × detected date | `marts.mart_executive_quality` |
| PartQuality | part | `marts.mart_part_quality` |
| BomIntegrity | parent assembly | `marts.mart_bom_integrity` |
| SupplierQuality | supplier | `marts.mart_supplier_quality` |
| BusinessImpact | part | `marts.mart_business_impact` |
| RemediationPerformance | decision date × decision × reviewer × severity × domain | `marts.mart_remediation_performance` |
| AIGovernance | provider × model × prompt version × call date | `marts.mart_ai_governance` |
| DimPart | part | `core.dim_part` |
| DimSupplier | supplier | `core.dim_supplier` |
| DimPlant | plant | `core.dim_plant` |
| DimDate | day | `core.dim_date` |

## Relationships (star schema)

| From (many) | To (one) | Key | Active |
|---|---|---|---|
| PartQuality | DimPart | part_key | yes |
| BusinessImpact | DimPart | part_key | yes |
| BomIntegrity | DimPart | parent_part_key → part_key | yes |
| SupplierQuality | DimSupplier | supplier_key | yes |
| PartQuality | DimPlant | primary_plant → plant_key | yes |
| BusinessImpact | DimPlant | primary_plant → plant_key | yes |
| ExecutiveQuality | DimDate | detected_date → date_key | yes |
| RemediationPerformance | DimDate | decision_date → date_key | yes |
| AIGovernance | DimDate | call_date → date_key | yes |

All relationships single-direction (dimension filters fact). No bidirectional
filtering; use measures for cross-fact analysis.

## Calculation-group recommendation

One calculation group `Time Intelligence` (requires Tabular Editor or PBI Desktop
model view): items `Current`, `MTD`, `QTD`, `YTD`, `PY` applied over `DimDate[date_key]`.

## Row-level security

Role **Plant Steward**: filter `DimPlant[plant_key] = LOOKUPVALUE(...)` against a
`UserPlantMap` table (username → plant). Ship `UserPlantMap` as a governed seed;
in the local fallback it is a CSV with a sample mapping. Apply the same filter to
DimPlant only — facts inherit via relationships.

## Refresh strategy

- Snowflake: scheduled import refresh 2×/day after the pipeline's dbt marts run;
  incremental refresh unnecessary at current volumes (< 5M rows).
- Local fallback: manual refresh after re-running the export script.
