# Changelog

All notable changes to BOM Guardian AI. Follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Hardening (H1–H10, post-M21)
- H1: reconciled stale/contradictory status wording; added
  `evaluation/claim-verification.json` (per-claim evidence + validation status).
  Corrections: the M9 "no entity leakage" claim and the ML P=1.00/R=1.00 headline are
  retired pending H2's leakage-safe re-evaluation; the M20 E2E test is relabeled
  service-level (it bypasses the real dbt project — H4 adds a true dbt-pipeline test);
  detection recall is clarified as recall-only over 17 SQL-mapped types (H3 adds
  precision + all 25 types); screenshots and GitHub Actions status marked explicitly
  pending; earlier "verified live/in-browser" phrasing replaced with what was actually
  exercised (accessibility tree + local tests).
- H2: enforced entity-disjoint ML evaluation. Candidate pairs form a graph over part
  ids; connected components become split groups; train/val/test part-set disjointness
  is asserted at runtime. Evaluated over 5 split seeds on a 4,000-part profile (409
  labeled duplicate pairs). Honest results (`evaluation/entity_resolution/ml_eval.json`):
  candidate-generation recall 0.95; logistic regression P 0.962±0.010 / R 0.804±0.178 /
  F1 0.867±0.113 (stable, recommended); gradient boosting P 0.769±0.431 / R 0.471±0.375
  (high-variance, not recommended at this scale) — retiring the earlier P=1.00/R=1.00.
  Reports candidate-generation recall separately so model recall is not read as
  end-to-end recall. Added connected-component, entity-disjointness, leak-rejection,
  and multi-seed tests.
- H3: strengthened defect-detection evaluation against a validated clean baseline.
  Generator fixes make the pre-injection baseline genuinely clean (active-only BOM
  components and demand; contiguous, non-overlapping revision windows) — validated by
  `scripts/validate_clean_baseline.py` (only 5 allowlisted statistical conditions fire).
  New baseline-diff evaluation covers all 25 injected types with subsystem attribution:
  SQL-detectable types recall 0.985 (194/197), precision >= 0.933 (conservative; false
  positives split into collateral vs spurious), per-type/per-difficulty/per-rule with
  explicit denominators. Duplicate types cross-referenced to entity resolution; 2 types
  documented as unevaluated. Added `scripts/validate_clean_baseline.py` and
  `tests/data_quality/test_clean_baseline.py`.
- H4: added a TRUE dbt end-to-end test (`tests/end_to_end/test_dbt_pipeline.py`) that
  invokes the real dbt project against a persistent DuckDB file, verifies all 11 core
  models and 7 marts build and populate, and runs the full engine + API + audited-approval
  loop against the dbt-built warehouse. Renamed the fast service-level test accordingly
  and added a fixture-drift guard so `TRANSFORM_SQL` cannot silently diverge from the dbt
  models.
- H5: completed/modernized the Snowflake execution path. Added a backend-agnostic
  `Warehouse` protocol and a `SnowflakeWarehouse` adapter (env-config, parameterized
  queries, `write_pandas` ingestion, existence/validation checks); moved the AI provider
  from legacy `SNOWFLAKE.CORTEX.COMPLETE` to `AI_COMPLETE` with a response schema, JSON
  validation, error handling, configurable model and latency capture; added
  `scripts/deploy_snowflake.py` (dry-run default), a scoped `SNOWFLAKE.CORTEX_USER`
  grant, and 12 fake-connection tests. Still never run against a live account.
- H6: added a configurable real AI provider (`AnthropicAIProvider`, optional `anthropic`
  extra) on the official SDK — schema-constrained JSON output, grounding validation via
  the engine, SDK retry/timeout, refusal handling, env-configured key/model
  (default `claude-opus-4-8`), token/latency audit, abstention, no data-write path. Added
  a provider factory, `scripts/validate_real_ai_provider.py` (skips without a key — no
  fabricated artifact), and 7 fake-client tests + a skipped-without-key integration test.
  Never called against the real API — external validation pending.
- H7: added role-based authorization to the API (`api/app/auth.py`). An
  analyst/steward/admin role ladder; `get_principal` resolves a Bearer token to a
  principal (401 on missing/unknown) and is enforced at the router level on every
  business route; approve/reject/request-evidence additionally require a steward or admin
  (`require_role`, 403 for analysts). The reviewer recorded on a decision is now the
  authenticated principal — the `reviewer` field was removed from the request body so an
  actor cannot be spoofed. Demonstration auth (static demo tokens, overridable via
  `BOMG_DEMO_USERS`), clearly labeled — not an enterprise IdP. The frontend signs in as a
  steward via a demo token (`VITE_DEMO_TOKEN`). Added 7 unit tests plus an API-level
  enforcement test (401/401/403, analyst-read allowed, issue never transitioned by denied
  attempts).
- H8: made GitHub Actions genuinely green (it had never passed; every prior run failed).
  Root cause: the python job installed `.[dev,api,ml]`, but the document-intelligence
  tests import `reportlab`/`pypdf` from the `docs-ai` extra, so pytest aborted during
  collection with exit code 2. Also fixed a latent `ruff format --check` failure on 8
  files. The python job now installs `.[dev,api,ml,docs-ai,dbt]`, adds a step asserting
  dbt is importable so the real dbt E2E test cannot silently skip, and runs `pytest -rs`.
  Verified on GitHub: run 29670834422 (commit `13fa952`) — python 3.12, python 3.13,
  frontend, dbt, docs-links, and secrets all successful. README CI badge added only
  after that confirmed run.
- H9: captured **real application screenshots** of all 8 UI surfaces (previously none
  existed). Added `scripts/capture_screenshots.py` — runs the real pipeline, starts
  FastAPI and the Vite dev server on runtime-selected free ports, waits for
  health/readiness, authenticates with the demo steward token, and drives the live UI
  with Playwright using ids read from the API; writes optimized PNGs plus a manifest with
  captions and alt text, and tears down the whole process tree in a `finally`. Exposed as
  `make screenshots` / `npm run screenshots`, with 8 harness regression tests. Also fixed
  a dead control the H7 authorization change had left behind: the Workbench's free-text
  "Reviewer name" input no longer had any effect, so it was replaced with the
  authenticated identity from a new `GET /api/v1/me` endpoint.
- H10: final forensic audit — published `docs/final-verification-report.md` sorting every
  claim into verified-on-CI / tested-locally / external-validation-pending /
  not-implemented / manual-remaining, with explicit denominators for every headline
  metric. Re-ran the full gate set in a clean CI-equivalent virtualenv. Five findings,
  all corrected: `docs/api-guide.md` still said "No authentication is implemented" and
  `docs/limitations.md` still claimed reviewer identity was self-declared (both stale
  since H7); the published endpoint count was wrong (the OpenAPI schema exposes **29**
  operations, not 25/26); `fetchPart` was dead code in the frontend API client; and the
  Workbench dead control (fixed in H9). Scans for TODO/FIXME markers, placeholder
  implementations, hard-coded secrets, committed generated files, frontend mock data,
  broken links, and legacy `CORTEX.COMPLETE` calls all came back clean. Honest completion
  re-derived at **93%** — deliberately not 100% while Snowflake, the Anthropic provider,
  and Power BI Desktop remain externally unvalidated.

### Added
- M0: repository governance, architecture docs, ADR log, ERD, DQ rule taxonomy,
  README skeleton, `.gitignore`, `.env.example`.
- M1: Python project configuration (`pyproject.toml`), settings module, structured
  JSON logging, unit tests, pre-commit config, Makefile, CI workflow skeleton,
  React + TypeScript + Vite frontend scaffold with vitest.
- M2: synthetic ERP generator — 22 datasets (part master, aliases, suppliers,
  supplier-parts, plants, warehouses, UOM, categories, BOM headers/components,
  revisions, ECOs, substitutions, supersessions, inventory, POs + lines, future
  demand, production orders, cost history, lead-time history, quotes), smoke/demo/full
  profiles, deterministic seeds, referential-integrity validation, multi-level acyclic
  BOMs by tier construction, Typer CLI, generation manifest with actual record counts,
  8 unit tests.
- M3: issue-injection engine — 25 controlled defect types (duplicates, missing/invalid
  attributes, BOM cycles/orphans/self-references, revision conflicts, anomalies,
  doc-vs-ERP discrepancies), difficulty levels, isolated ground-truth labels and
  injection manifest, `--inject` CLI flag, 9 unit tests.
- M4: Snowflake provisioning scripts (schemas, warehouses, roles/grants, stages,
  teardown — authored, deployment pending) and DuckDB `LocalWarehouse` with the same
  7-layer schema layout, 5 unit tests.
- M5: auditable ingestion — audit columns (hashes, batch, sequence, status), file-hash
  idempotency, null-PK rejection handling, ops audit tables, isolated ground-truth
  loading, 5 integration tests.
- M6: dbt transformation layer — 22 sources, 10 staging views with adapter-safe
  normalization macros, 11 core dims/facts, part-master snapshot, 28 schema tests,
  DuckDB local target, `scripts/run_local_pipeline.py` end-to-end runner.
- M7: data-quality engine — 49-rule registry across 9 domains, execution engine with
  issues + evidence + per-rule failure isolation, transparent entity/BOM/enterprise
  scoring, 17 tests incl. ground-truth detection verification.
- M8: explainable ER baseline — blocking, 11 interpretable features, weighted matcher
  with confidence bands + evidence, measured evaluation artifact (recommend band
  P=1.00/R=0.57 on smoke), 8 tests.
- M9: ML entity resolution — LR + gradient boosting, group-aware splits, precision-floor
  threshold selection, model persistence, model card, measured comparison report
  6 tests. (Metrics re-measured leakage-safe in H2 → `evaluation/entity_resolution/ml_eval.json`.)
- M10: field-level golden-record survivorship — reliability/recency/agreement scoring,
  domain source preferences, full lineage with alternatives + confidence, reversible,
  9 tests.
- M11: BOM graph intelligence — cycle/self-ref/orphan validation, depth, reverse
  dependencies, path tracing, expansion, centrality, criticality, supplier
  concentration, 16 tests.
- M12: document intelligence — synthetic quote PDFs (incl. injection-attempt fixtures),
  deterministic extraction with evidence/confidence/review routing, prompt-injection
  flagging, ERP discrepancy comparison, 8 tests.
- M13: governed AI remediation engine — provider interface (mock tested, Cortex
  pending), strict proposal schema (no approve action, mandatory human review),
  grounding validation, abstention, AI-call audit table, 10 tests.
- M14: Quality Impact Twin — blast-radius exposure metrics with documented priority
  weights, merge/field-correction/component-replacement counterfactual scenarios with
  before/after diffs and new-conflict warnings, scenario-only persistence, verified
  baseline immutability, 9 tests.
- M15: FastAPI service — 24 versioned endpoints (parts, issues + human decision
  workflow, BOM graph, scenarios, analytics), correlation IDs, structured errors,
  restricted CORS, OpenAPI, 13 API tests on real pipeline data.
- M16: React remediation workbench — 8 surfaces over the live API (no mock data),
  cytoscape BOM explorer, approval workflow, scenario before/after, AI-governance
  dashboard; verified in-browser; DuckDB thread-safety fix; 5 frontend tests.
- M17: Data Steward Copilot — allowlisted read-only tools, keyword classification,
  cited evidence, mutation refusal, insufficient-evidence handling, API endpoint +
  UI page, 8 tests.
- M18: Power BI package — 7 dbt analytics marts, semantic-model spec, 30+ DAX measures,
  theme, page specs with RLS/refresh/drill-through design, CSV fallback exporter;
  Desktop validation honestly marked pending.
- M19: CI/security — dbt smoke-pipeline CI job, docs link check, dependency review,
  optional manual Snowflake workflow, security threat model + AI governance docs.
- M20: end-to-end evaluation — 12-step E2E test, detection-recall report (100% on 156
  mapped injected defects), measured smoke/demo benchmarks, measured profile counts
  incl. full profile (1,699,010 records / 735s generation).
- M21: portfolio packaging — final README with measured results and honest status
  table, data dictionary, API guide, limitations, demo script; hygiene audit clean
  (no TODOs, no secrets, all local doc links resolve).
