# Business Case — BOM Guardian AI

## The problem

Mid-size and large manufacturers typically run several source systems — ERP, PLM/engineering,
supplier portals, and legacy plants acquired through M&A. Master data (parts, suppliers,
BOMs) diverges across them:

- **Duplicate parts** — the same physical component exists under multiple part numbers
  (different plants, formats, or source systems), inflating inventory and fragmenting
  purchasing leverage.
- **Duplicate / conflicting suppliers** — the same vendor exists multiple times with
  different names, currencies, or payment terms.
- **Broken BOM structures** — orphan components, circular references, obsolete parts in
  active assemblies, overlapping engineering-revision effectivity.
- **Stale operational attributes** — wrong lead times and standard costs drive bad MRP
  output: expedites, shortages, and excess stock.

Industry practitioners consistently rank material master and BOM data among the most
defect-prone domains in manufacturing, and each undetected defect propagates: one bad
lead time on a shared component distorts the plan of every assembly above it.

## Why current approaches fall short

| Approach | Gap |
|---|---|
| Periodic manual data cleanses | Point-in-time; defects reaccumulate immediately |
| Generic DQ dashboards | Count defects but don't prioritize by business impact |
| Hard ERP validation rules | Catch entry errors, not cross-system conflicts or duplicates |
| Black-box MDM matching | Unexplainable merges erode steward trust; wrong merges are operationally damaging |

## What BOM Guardian AI does differently

1. **Impact-ranked remediation** — every defect gets a blast-radius calculation
   (assemblies affected, future demand exposed, inventory and PO value at risk), so
   stewards fix what matters first, not what alphabetizes first.
2. **Explainable entity resolution** — duplicate-part and supplier matching uses
   transparent features and interpretable models, with evidence attached to every match.
3. **Field-level golden records** — survivorship selects the best value per field with
   recorded lineage, source, reason, and alternatives; fully reversible.
4. **Counterfactual simulation** — proposed fixes are simulated (before/after) without
   touching baseline data, surfacing newly resolved rules and newly introduced conflicts
   before anyone approves anything.
5. **Governed AI, human-approved changes** — AI drafts structured, evidence-grounded
   proposals and may abstain; only a human can approve, and every decision is audited.

## Stakeholders and value

| Stakeholder | Value |
|---|---|
| Data stewards / MDM team | Prioritized queue, evidence, one-click simulation, audit trail |
| Supply chain planners | Fewer MRP distortions from bad lead times/costs |
| Procurement | Consolidated supplier view, price-conflict detection |
| Engineering | BOM integrity, revision-effectivity conflicts surfaced |
| Executives | Enterprise quality score, exposure trends, remediation throughput (Power BI) |

## Success measures (evaluated against injected ground truth)

- Detection precision/recall by defect type
- Entity-resolution precision (precision-favored: bad merges are costly)
- Golden-record field-level accuracy
- Blast-radius coverage of exposed demand/inventory value
- Simulated remediation acceptance rate and time-to-closure

All data is synthetic; all metrics are produced by reproducible evaluation runs against
injected ground-truth labels — see `docs/limitations.md` (added later) for boundaries.
