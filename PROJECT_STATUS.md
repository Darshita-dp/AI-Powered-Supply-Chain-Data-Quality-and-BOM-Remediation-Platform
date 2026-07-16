# PROJECT_STATUS.md — BOM Guardian AI

_Last updated: 2026-07-16_

## Current milestone

**M6 — dbt transformation layer** (next up)

## Milestone plan

| # | Milestone | Status |
|---|-----------|--------|
| M0 | Repository governance and architecture | ✅ Complete |
| M1 | Engineering foundation | ✅ Complete |
| M2 | Synthetic ERP generator | ✅ Complete |
| M3 | Controlled issue injection and ground truth | ✅ Complete |
| M4 | Snowflake and local warehouse setup | ✅ Complete (Snowflake scripts authored, deployment pending — no credentials) |
| M5 | Auditable ingestion | ✅ Complete |
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
- **M4** — Snowflake provisioning scripts (database + 7 layer schemas, XS/S warehouses
  with auto-suspend, 4-role security model with grants, stages/file formats, teardown;
  **authored and reviewed but NOT executed — no Snowflake credentials, deployment
  pending**) and the DuckDB `LocalWarehouse` with the same 7-layer schema layout,
  load/query/validate API, 5 unit tests.
- **M5** — `IngestionService`: raw-layer loads with audit columns (batch ID, timestamps,
  file/row SHA-256 hashes, schema version, record sequence, load status), file-hash
  idempotency (re-ingest loads 0 rows), null-PK rejection to `ops.rejected_records`,
  batch/file audit tables, isolated ground-truth loading. 5 integration tests.

## In-progress work

- None; next is M2.

## Last successful commit

- See `git log` (M1 commit).

## Tests currently passing

- Python: 31 tests — 26 unit + 5 integration (`pytest`), ruff + ruff-format + mypy clean.
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

Start M6: dbt project `dbt_supply_chain/` — sources over raw, staging models
(normalization preserving originals), core dims/facts, snapshots, contracts, tests,
docs, DuckDB local target. Commit
`feat: build governed dbt supply chain transformation models`.

## Honest completion percentage

**~24%** — generation, injection, warehouse, and ingestion done; dbt, quality engine,
ML, API, and frontend still pending.
