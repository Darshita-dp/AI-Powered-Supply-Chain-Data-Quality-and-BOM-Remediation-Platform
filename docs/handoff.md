# Handoff Guide — BOM Guardian AI

Restart instructions for a new Claude session.

## Continuation instruction

Read `CLAUDE.md`, `PROJECT_STATUS.md`, and this file. Inspect the repository and git
history, verify the current test state, and continue from the next incomplete milestone
in `PROJECT_STATUS.md` without rebuilding completed work.

## Current state (2026-07-16, later)

- M0–M14 complete and pushed (see `PROJECT_STATUS.md` milestone table and `git log`).
- 114 Python tests passing; ruff/mypy clean; frontend scaffold builds.
- Local pipeline: `python scripts/run_local_pipeline.py` (generate → inject → ingest →
  dbt build). ER evaluation: `scripts/evaluate_entity_resolution.py`,
  `scripts/train_entity_resolution.py` (artifacts in `evaluation/`).
- Next: M15 FastAPI service (`api/`), then M16 frontend, M17 copilot, M18 Power BI,
  M19 CI/security, M20 E2E evaluation, M21 packaging.

## Environment notes

- Windows 11; Python 3.13.12, Node 24.18.0, npm 11.16.0 on PATH. `gh` CLI **not**
  installed — use plain git over HTTPS.
- Git identity configured: Darshita Patel / darshitaa2001@gmail.com.
- No Snowflake credentials; use DuckDB local fallback throughout.
- No Anthropic API key required; tests use the deterministic mock AI provider.
- Power BI Desktop availability unverified.

## Key rules to re-read

Truthfulness/anti-overclaiming, no AI auto-approval of remediation, simulation never
mutates baseline, ground truth isolated from model inputs — all in `CLAUDE.md`.
