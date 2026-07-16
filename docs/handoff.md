# Handoff Guide — BOM Guardian AI

Restart instructions for a new Claude session.

## Continuation instruction

Read `CLAUDE.md`, `PROJECT_STATUS.md`, and this file. Inspect the repository and git
history, verify the current test state, and continue from the next incomplete milestone
in `PROJECT_STATUS.md` without rebuilding completed work.

## Current state (2026-07-16)

- Repo cloned to `C:\Projects\AI-Powered Supply Chain Data Quality and BOM Remediation Platform`
  from `Darshita-dp/AI-Powered-Supply-Chain-Data-Quality-and-BOM-Remediation-Platform`.
- M0 (governance/architecture docs) authored this session; commit pending/just made —
  check `git log`.
- No executable code yet. M1 (engineering foundation) is next.

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
