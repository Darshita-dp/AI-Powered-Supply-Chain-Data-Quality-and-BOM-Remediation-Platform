# Data-Quality Rule Taxonomy — BOM Guardian AI

Design taxonomy for the rule engine (implemented in M7). Each implemented rule will carry:
rule ID, name, description, domain, severity, rule type, owning role, threshold, enabled
flag, version, implementation reference, effective date, and remediation guidance. This
catalog is the target set (~45 rules); the implemented registry is the source of truth
once M7 lands.

Severity scale: `critical` > `high` > `medium` > `low`.

## Completeness (COMP)

| ID | Rule | Severity |
|---|---|---|
| COMP-001 | Part missing description | high |
| COMP-002 | Part missing category | medium |
| COMP-003 | Part missing UOM | critical |
| COMP-004 | Purchased part missing supplier | high |
| COMP-005 | Part missing lead time | high |
| COMP-006 | Part missing standard cost | high |
| COMP-007 | Part missing plant assignment | medium |
| COMP-008 | Part missing manufacturer part number | low |

## Uniqueness (UNIQ)

| ID | Rule | Severity |
|---|---|---|
| UNIQ-001 | Duplicate source part number within source system | critical |
| UNIQ-002 | Duplicate normalized part number across sources | high |
| UNIQ-003 | Duplicate supplier identifier | critical |
| UNIQ-004 | Multiple active golden records for one entity | critical |
| UNIQ-005 | Multiple active engineering revisions for one part | high |

## Validity (VALD)

| ID | Rule | Severity |
|---|---|---|
| VALD-001 | Invalid UOM code | high |
| VALD-002 | Invalid currency code | high |
| VALD-003 | Invalid lifecycle status | medium |
| VALD-004 | Non-positive standard cost | high |
| VALD-005 | Negative lead time | high |
| VALD-006 | Non-positive BOM component quantity | critical |
| VALD-007 | End date before start date | high |

## Referential integrity (REFI)

| ID | Rule | Severity |
|---|---|---|
| REFI-001 | BOM component references missing parent part | critical |
| REFI-002 | BOM component references missing child part | critical |
| REFI-003 | Supplier-part link references missing supplier | high |
| REFI-004 | Record references missing plant | high |
| REFI-005 | Future demand references missing part | high |
| REFI-006 | Cost history references missing part | medium |

## Cross-field consistency (XFLD)

| ID | Rule | Severity |
|---|---|---|
| XFLD-001 | Purchased part without any supplier relationship | high |
| XFLD-002 | Manufactured part without a BOM | high |
| XFLD-003 | Obsolete part with future demand | critical |
| XFLD-004 | Blocked component in an active BOM | critical |
| XFLD-005 | Currency inconsistent with supplier/plant | medium |
| XFLD-006 | Part category inconsistent with UOM | low |

## Temporal consistency (TEMP)

| ID | Rule | Severity |
|---|---|---|
| TEMP-001 | Overlapping BOM effectivity dates | high |
| TEMP-002 | Multiple simultaneously active revisions | high |
| TEMP-003 | Effectivity end before start | high |
| TEMP-004 | Stale authoritative record (no update within threshold) | medium |
| TEMP-005 | Newer source value overwritten by older source | high |

## Anomalies (ANOM)

| ID | Rule | Severity |
|---|---|---|
| ANOM-001 | Extreme standard-cost movement | high |
| ANOM-002 | Extreme lead-time movement | high |
| ANOM-003 | Negative inventory quantity | high |
| ANOM-004 | Demand spike vs. history | medium |
| ANOM-005 | Supplier price variance for same part | medium |
| ANOM-006 | Extreme BOM component quantity | medium |

## Graph integrity (GRPH)

| ID | Rule | Severity |
|---|---|---|
| GRPH-001 | Circular BOM reference | critical |
| GRPH-002 | Self-referencing BOM | critical |
| GRPH-003 | Orphan BOM node | high |
| GRPH-004 | Excessive BOM depth | medium |
| GRPH-005 | Suspiciously high parent count for a component | low |
| GRPH-006 | Disconnected active assembly | medium |

## Document/ERP reconciliation (DOCR)

| ID | Rule | Severity |
|---|---|---|
| DOCR-001 | Supplier-document price conflicts with ERP | high |
| DOCR-002 | Supplier-document lead time conflicts with ERP | high |
| DOCR-003 | Conflicting manufacturer part numbers across sources | medium |
