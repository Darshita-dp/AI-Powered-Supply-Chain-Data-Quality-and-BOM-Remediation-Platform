# PROJECT_STATUS.md — BOM Guardian AI

_Last updated: 2026-07-16_

## Current milestone

**M2 — Synthetic ERP generator** (next up)

## Milestone plan

| # | Milestone | Status |
|---|-----------|--------|
| M0 | Repository governance and architecture | ✅ Complete |
| M1 | Engineering foundation | ✅ Complete |
| M2 | Synthetic ERP generator | ⬜ Not started |
| M3 | Controlled issue injection and ground truth | ⬜ Not started |
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

## In-progress work

- None; next is M2.

## Last successful commit

- See `git log` (M1 commit).

## Tests currently passing

- Python: 4 unit tests (`pytest`), ruff + ruff-format + mypy clean.
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

Start M2: implement `data_generator/` (config, generators for all master/operational
datasets, smoke/demo/full profiles, stable seeds, CLI, generation manifest,
record-count report) with tests. Commit
`feat: generate realistic synthetic ERP and supply chain data`.

## Honest completion percentage

**~8%** — governance docs and engineering foundation only; no domain functionality yet.
