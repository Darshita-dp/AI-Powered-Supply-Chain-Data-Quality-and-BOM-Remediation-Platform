# Handoff Guide — BOM Guardian AI

Restart instructions for a new Claude session.

## Continuation instruction

Read `CLAUDE.md`, `PROJECT_STATUS.md`, and this file. Inspect the repository and git
history, verify the current test state, and continue from the next incomplete milestone
in `PROJECT_STATUS.md` without rebuilding completed work.

## Current state (2026-07-16, end of build)

- **All milestones M0–M21 complete and pushed.** 136 Python + 5 frontend tests pass;
  ruff/mypy/typecheck/build clean; evaluation artifacts in `evaluation/`.
- Pipeline: `python scripts/run_local_pipeline.py`; API: `uvicorn api.app.main:app`;
  UI: `cd frontend && npm run dev`. Demo walkthrough: `docs/demo-script.md`.
- Open external items only: Snowflake deployment (needs account), Power BI Desktop
  validation (`powerbi/BUILD_POWER_BI.md`), GitHub Actions run confirmation,
  application screenshots.

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
