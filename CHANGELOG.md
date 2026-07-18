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
