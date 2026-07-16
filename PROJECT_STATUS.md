# PROJECT_STATUS.md — BOM Guardian AI

_Last updated: 2026-07-16_

## Current milestone

**M4 — Snowflake and local warehouse setup** (next up)

## Milestone plan

| # | Milestone | Status |
|---|-----------|--------|
| M0 | Repository governance and architecture | ✅ Complete |
| M1 | Engineering foundation | ✅ Complete |
| M2 | Synthetic ERP generator | ✅ Complete |
| M3 | Controlled issue injection and ground truth | ✅ Complete |
| M4 | Snowflake and local warehouse setup | ⬜ Not started |
| M5 | Auditable ingestion | ⬜ Not started |
| M6 | dbt transformation layer | ⬜ Not started |
| M7 | Data-quality engine (40+ rules) | ⬜ Not started |
| M8 | Entity-resolution baseline | ⬜ Not started |
| M9 | ML entity resolution | ⬜ Not started |
| M10 | Golden-record survivorship | ⬜ Not started |
| M11 | BOM graph intelligence | ⬜ Not started |
| M12 | Document intelligence | ⬜ Not started |
| M13 | AI remediation engine | ⬜ Not started |
| M14 | Quality Impact Twin | ⬜ Not started |
| M15 | FastAPI service | ⬜ Not started |
| M16 | React remediation workbench | ⬜ Not started |
| M17 | Data Steward Copilot | ⬜ Not started |
| M18 | Power BI analytical package | ⬜ Not started |
| M19 | CI, security, observability | ⬜ Not started |
| M20 | End-to-end evaluation | ⬜ Not started |
| M21 | Portfolio packaging | ⬜ Not started |

## Completed milestones

- **M0** — governance docs, architecture overview, ADR log (6 ADRs), ERD, DQ rule
  taxonomy (~45 rules), README skeleton, `.gitignore`, `.env.example`.
  Commit `994e6b5`, pushed.
- **M1** — `pyproject.toml` (ruff/mypy/pytest config, dependency groups), settings
  module (pydantic-settings, local-first defaults), structured JSON logging (structlog),
  4 passing unit tests, pre-commit config, Makefile, GitHub Actions CI skeleton
  (Python 3.12/3.13 matrix + frontend + gitleaks), Vite React-TS frontend with
  TanStack Query/router/vitest installed, app shell + 1 passing component test,
  CONTRIBUTING/SECURITY/CHANGELOG.
- **M2** — synthetic ERP generator: 22 datasets, smoke/demo/full profiles, deterministic
  seeds, referential-integrity validation, tier-constructed multi-level acyclic BOMs,
  Typer CLI, manifest with measured counts. Measured runs: smoke = 13,843 records
  (1.2s), demo = 247,881 records (13.5s); full profile configured but not yet executed
  (scheduled for M20 performance evaluation). 8 unit tests.
- **M3** — issue-injection engine: all 25 defect types with easy/medium/hard difficulty,
  ground-truth labels (injection ID, record, field, original/injected/correct values,
  matching entity, seed) written to a separate `ground_truth/` directory, injection
  manifest, `--inject` CLI flag. Smoke run with defaults injects ~250 labeled defects.
  9 unit tests proving correct injection (incl. cycle creation, orphan refs,
  determinism, clean-baseline isolation).

## In-progress work

- None; next is M2.

## Last successful commit

- See `git log` (M1 commit).

## Tests currently passing

- Python: 21 unit tests (`pytest`), ruff + ruff-format + mypy clean.
- Frontend: 1 vitest test, oxlint clean, `tsc -b` clean, production build succeeds.
- CI workflow authored but not yet observed passing on GitHub (validates on push).

## Known failures

- None.

## External integrations

**Configured:** none.

**Not configured:**
- Snowflake (no credentials — local DuckDB fallback is the plan; Snowflake scripts will
  be authored but deployment status will be documented honestly)
- GitHub push auth: clone over HTTPS worked; push not yet attempted
- Power BI Desktop: availability unverified; fallback is a full source/build package
- Anthropic or other hosted AI provider: optional, not required for core tests

## Next exact action

Start M4: Snowflake setup scripts (`warehouse/snowflake/` — database/schemas, roles and
grants, warehouses, stages, file formats, teardown) plus the DuckDB local warehouse
module (`warehouse/local/`), with setup validation. Commit
`feat: provision Snowflake target and local warehouse fallback`.

## Honest completion percentage

**~17%** — data generation and defect injection done; warehouse, quality engine, ML,
API, and frontend functionality still pending.
