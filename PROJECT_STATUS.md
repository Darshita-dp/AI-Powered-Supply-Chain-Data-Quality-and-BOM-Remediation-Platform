# PROJECT_STATUS.md — BOM Guardian AI

_Last updated: 2026-07-16_

## Current milestone

**M13 — AI remediation engine** (next up)

## Milestone plan

| # | Milestone | Status |
|---|-----------|--------|
| M0 | Repository governance and architecture | ✅ Complete |
| M1 | Engineering foundation | ✅ Complete |
| M2 | Synthetic ERP generator | ✅ Complete |
| M3 | Controlled issue injection and ground truth | ✅ Complete |
| M4 | Snowflake and local warehouse setup | ✅ Complete (Snowflake scripts authored, deployment pending — no credentials) |
| M5 | Auditable ingestion | ✅ Complete |
| M6 | dbt transformation layer | ✅ Complete |
| M7 | Data-quality engine (40+ rules) | ✅ Complete |
| M8 | Entity-resolution baseline | ✅ Complete |
| M9 | ML entity resolution | ✅ Complete |
| M10 | Golden-record survivorship | ✅ Complete |
| M11 | BOM graph intelligence | ✅ Complete |
| M12 | Document intelligence | ✅ Complete |
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
- **M6** — dbt project: 22 raw sources, 10 staging views (normalization with originals
  preserved, adapter-safe macros for DuckDB + Snowflake), 11 core dims/facts, part
  snapshot, 28 schema tests (structural = error, content = warn since defects are
  intentionally present), local DuckDB target. Verified run:
  `python scripts/run_local_pipeline.py` → dbt build PASS=47 WARN=3 ERROR=0 (warnings
  are the injected orphans/missing UOMs, as designed).
- **M7** — quality engine: registry of 49 executable rules across 9 domains
  (completeness, uniqueness, validity, referential, cross-field, temporal, anomaly,
  graph-SQL subset, doc reconciliation), `RuleEngine` persisting rules/executions/
  issues/evidence to the quality schema with per-rule failure isolation,
  `QualityScorer` (entity, BOM, business-weighted enterprise scores with documented
  weights). 17 tests, including ground-truth detection checks for 10 injected defect
  types (100% of those injected records flagged) and ground-truth isolation.
- **M8** — ER baseline: normalization, 3-key blocking (PN prefix / MPN / category+token,
  oversized-block guard), 11 interpretable pair features, weighted deterministic matcher
  with recommend/review/abstain bands and per-match evidence. Measured on smoke
  (`evaluation/entity_resolution/baseline_smoke.json`, reproducible via
  `scripts/evaluate_entity_resolution.py`): recommend band precision 1.00 / recall 0.57;
  review band precision 1.00 / recall 0.86. 8 tests.
- **M9** — ML ER: LR + gradient boosting over the same 11 features, group-aware
  60/20/20 splits (no entity leakage), validation threshold selection with a 0.95
  precision floor, joblib persistence, LR coefficients exported for explainability,
  model card (`docs/model-card.md`) with honest caveats about small test-set size.
  Measured on smoke (`evaluation/entity_resolution/ml_smoke.json`): LR P=1.00/R=0.83,
  GB P=1.00/R=1.00 on held-out test split (~6 positives — wide uncertainty, noted).
  6 tests.
- **M10** — golden-record survivorship: field-level selection over 9 governed fields
  scored on source reliability + recency + cross-source agreement with documented
  domain preferences (engineering→description, ERP→cost, supplier portal→lead time);
  every decision carries source record/system, reason, confidence, timestamp, version,
  and all alternatives (reversible); no warehouse mutation. 9 tests.
- **M11** — `BomGraph` (NetworkX): cycles/self-refs/orphans-by-role validation,
  roots/leaves/longest-chain depth (cycle-safe), dependencies + reverse dependencies,
  bounded path tracing, level-aware subassembly expansion, degree centrality,
  demand-weighted criticality, single-source supplier concentration. 16 tests covering
  every required shape (acyclic, direct + multi-level cycle, self-ref, disconnected,
  deep, shared component, reverse traversal).
- **M12** — document intelligence: synthetic supplier quote PDFs (reportlab) with a
  configurable fraction containing prompt-injection attempts; deterministic regex
  extraction (pypdf) with per-field evidence line, page number, confidence, and
  review routing below 0.8; type/allowed-set validation; injection detection that
  flags instruction-like content without ever following it; ERP comparison producing
  price/lead-time discrepancy records. 8 integration tests (extraction exactness,
  injection resilience, discrepancy detection).

## In-progress work

- None; next is M2.

## Last successful commit

- See `git log` (M1 commit).

## Tests currently passing

- Python: 95 tests — unit + integration + data-quality (`pytest`), ruff + mypy clean.
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

Start M13: AI remediation engine in `src/bom_guardian/ai/` + `remediation/` — provider
interface (`DeterministicMockAIProvider`, `SnowflakeCortexAIProvider` stub, optional
Anthropic), strict Pydantic proposal schema, evidence-grounded explanations, abstention,
audit logging, no write path to golden state. Commit
`feat: generate governed AI remediation proposals`.

## Honest completion percentage

**~56%** — through document intelligence; AI engine, impact twin, API, frontend,
Power BI still pending.
