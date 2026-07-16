# BOM Guardian AI

**AI-Powered Supply Chain Data Quality and BOM Remediation Platform**

BOM Guardian AI detects supply-chain master-data and bill-of-materials defects, resolves
duplicate parts and suppliers into explainable golden records, calculates the downstream
business "blast radius" of every defect, and routes AI-generated remediation proposals
through a governed human-approval workflow.

> **Status: early development.** This README is a skeleton; sections are filled in as the
> corresponding capability is actually built and validated. See
> [PROJECT_STATUS.md](PROJECT_STATUS.md) for the honest, current state of the project.

## Implementation status

| Capability | Status |
|---|---|
| Repository governance & architecture docs | Implemented |
| Engineering foundation (tooling, CI skeleton, frontend scaffold) | Planned |
| Synthetic ERP data generator (smoke / demo / full profiles) | Planned |
| Controlled issue injection with ground truth | Planned |
| Snowflake scripts + DuckDB local warehouse | Planned |
| Auditable ingestion | Planned |
| dbt transformation layer | Planned |
| Data-quality rule engine (40+ rules) | Planned |
| Entity resolution (baseline + ML) | Planned |
| Golden-record survivorship | Planned |
| BOM graph intelligence | Planned |
| Document intelligence | Planned |
| AI remediation engine | Planned |
| Quality Impact Twin | Planned |
| FastAPI service | Planned |
| React remediation workbench | Planned |
| Data Steward Copilot | Planned |
| Power BI analytical package | Planned |
| CI, security, observability | Planned |
| End-to-end evaluation | Planned |

## The business problem

Manufacturing ERP landscapes accumulate duplicate parts, conflicting supplier records,
broken BOM links, obsolete components in active assemblies, and stale costs and lead
times. These defects silently drive excess inventory, production stoppages, and wrong
purchasing decisions. Most data-quality tooling counts defects; it does not tell you
**which defect to fix first, what the fix should be, or what breaks downstream if you
fix it wrong**. Full case: [docs/business-case.md](docs/business-case.md).

## Unique differentiator — the Quality Impact Twin

For every significant defect, the platform computes its downstream blast radius —
affected assemblies, exposed future demand, inventory and purchase-order value at risk,
suppliers and plants involved — and simulates remediation counterfactuals (merge, field
correction, component replacement) **without mutating baseline data**, showing a full
before/after comparison prior to human approval.

## Architecture

See [docs/architecture/overview.md](docs/architecture/overview.md),
[docs/diagrams/erd.md](docs/diagrams/erd.md), and
[docs/architecture-decisions.md](docs/architecture-decisions.md).

Planned stack: Python 3.12+ · Snowflake (DuckDB local fallback) · dbt · FastAPI ·
React + TypeScript + Vite · Power BI · GitHub Actions.

## Getting started

Setup instructions will be added when the engineering foundation (M1) lands.

## Synthetic-data disclaimer

All data in this project is synthetically generated. No real supplier, part, pricing, or
company data is used anywhere in the repository.

## License

[MIT](LICENSE)
