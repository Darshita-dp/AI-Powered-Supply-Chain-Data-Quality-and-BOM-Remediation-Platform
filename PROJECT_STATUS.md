# PROJECT_STATUS.md — BOM Guardian AI

_Last updated: 2026-07-17 (hardening phase)_

## Current milestone

**M0–M21 built and locally tested. Now in the H1–H10 hardening phase** (accuracy,
validation, and production-hardening; see the hardening table below).

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
| M13 | AI remediation engine | ✅ Complete (mock provider tested; Cortex path pending credentials) |
| M14 | Quality Impact Twin | ✅ Complete |
| M15 | FastAPI service | ✅ Complete |
| M16 | React remediation workbench | ✅ Complete (live API data; 5 vitest tests + build; browser rendering exercised via accessibility tree — screenshots pending H9) |
| M17 | Data Steward Copilot | ✅ Complete (deterministic classifier; AI rewrite optional later) |
| M18 | Power BI analytical package | ✅ Complete (source package; Desktop validation pending — no `.pbix` claimed) |
| M19 | CI, security, observability | ✅ Complete (workflows authored; GitHub run status verifies on push) |
| M20 | End-to-end evaluation | ✅ Complete |
| M21 | Portfolio packaging | ✅ Complete (no screenshots — capture unavailable; documented honestly) |

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
- **M9** — ML ER: LR + gradient boosting over the same 11 features, GroupShuffleSplit
  60/20/20, validation threshold selection with a 0.95 precision floor, joblib
  persistence, LR coefficients exported for explainability, model card
  (`docs/model-card.md`). 6 tests.
  ⚠️ **Superseded by H2:** the M9 grouping keyed only on the first part ID, which does
  **not** guarantee entity-disjoint folds — the "no entity leakage" claim was not
  actually enforced. H2 replaces it with connected-component splitting and re-measures;
  the P=1.00/R=1.00 headline is retired. See the H2 evaluation artifacts and model card.
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
- **M13** — AI remediation engine: `AIProvider` interface with
  `DeterministicMockAIProvider` (tested) and `SnowflakeCortexAIProvider` (implemented,
  external validation pending — no credentials); strict Pydantic proposal schema with
  schema-level guarantees (no approve action exists; `human_review_required` cannot be
  false); grounding validation rejecting fabricated evidence refs; abstention on sparse
  evidence; per-call audit (provider, model, prompt version, sizes, latency, validation
  result) in `quality.ai_call_audit`. 10 tests.
- **M14** — Quality Impact Twin: blast-radius calculation (affected assemblies,
  downstream components, dependency depth, demand/inventory/PO exposure, production
  orders, suppliers, plants, revisions, supplier concentration, cost exposure,
  documented priority weighting) plus counterfactual scenarios (merge, field
  correction, component replacement) with full before/after comparison, resolved-rule
  and new-warning detection (e.g. merging into an obsolete part, replacement causing a
  cycle), persistence to `quality.scenarios` only, and verified zero mutation of
  baseline data. 9 tests.
- **M15** — FastAPI service (`api/`): 24 versioned `/api/v1` endpoints — health/
  readiness/metrics; parts (paginated list with search/filter/sort, detail, sources,
  golden-record lineage, impact); issues (filterable list, detail, evidence, history,
  mock-AI recommendations, human approve/reject/request-evidence with lifecycle guards
  and decision audit); BOM graph/dependencies/reverse-dependencies; scenario simulation
  + retrieval; analytics (quality, business-impact, remediation, AI-governance).
  Correlation-ID middleware, restricted CORS, structured errors without stack traces,
  OpenAPI at `/api/v1/docs`. 13 API tests against real pipeline data (no mocks);
  copilot endpoint arrives in M17.
- **M16** — React workbench: 7 routes covering the 8 required surfaces (Command Center;
  DQ Explorer with severity/domain/status/rule filters + pagination; Issue Detail inside
  the Remediation Workbench with evidence, AI recommendation, approve/reject and
  decision history; Part 360 with golden-record lineage + blast radius + issues; BOM
  Graph Explorer with cytoscape rendering, cycle/lifecycle color coding, depth control,
  reverse dependencies; Scenario Simulator with before/after + resolved rules + new
  warnings; AI Governance metrics). All data flows through the live API (no mock data);
  loading/empty/error states; industrial navy design; responsive sidebar. Verified in
  the browser against the smoke-pipeline warehouse (Command Center KPIs, issue detail,
  recommendation generation observed working). 5 vitest tests; typecheck/lint/build
  clean. Found+fixed a DuckDB thread-safety issue under concurrent API requests.
- **M17** — Steward Copilot: 8 allowlisted read-only tools (fixed parameterized SELECTs
  — no free-form SQL), deterministic keyword classification, cited answers
  (table:record citations), refusal of approve/apply/mutation requests, explicit
  insufficient-evidence handling, `POST /api/v1/copilot/query`, Copilot UI page with
  example questions. 8 tests incl. a source-level read-only guarantee check.
- **M18** — Power BI package: 7 dbt analytics marts (executive, part, BOM, supplier,
  business-impact, remediation, AI-governance) building green in the local pipeline
  (`PASS=7`); semantic-model spec (11 tables, star relationships, RLS, refresh); 30+
  measure DAX catalog; industrial theme JSON; page-by-page report spec with tooltips
  and drill-through; CSV fallback via `scripts/export_powerbi_data.py` (verified: 11
  extracts). **Power BI Desktop not operated — no `.pbix` exists; validation pending**
  per `powerbi/BUILD_POWER_BI.md`.
- **M19** — CI/security: CI extended with a dbt job running the full smoke pipeline,
  markdown link check (lychee, offline), dependency review on PRs, gitleaks; optional
  manual Snowflake validation workflow that skips cleanly without secrets;
  `docs/security-model.md` (controls, 10-risk threat model, honest gaps incl. no
  API authentication) and `docs/ai-governance.md` (guarantees + provider status).
  All local equivalents of CI checks pass; GitHub Actions run status to be confirmed
  after push.
- **M20** — E2E evaluation: 12-step end-to-end test passing (generation → injection →
  ingest → transform → rules → ER → issue → impact → mock recommendation → API →
  audited human approval → baseline-immutability check); detection-recall report
  (`evaluation/data_quality/detection_smoke.json`): **100% recall on 156 mapped
  injected defects across 17 issue types**, 8 unmapped types documented; measured
  benchmarks for smoke (`benchmarks_smoke.json`: rules 0.44s, ER 0.21s, API lists
  ~10ms) and demo (`benchmarks_demo.json`: generate 12.3s, ingest 18.5s, rules 0.9s,
  ER 66.6s); profile counts measured (`profile_counts.json`): smoke 13,882 / demo
  247,881 / **full 1,699,010 records generated in 735s** (full-profile downstream
  stages not run — documented). 136 Python tests total.
  ⚠️ **Refined by H4:** the M20 end-to-end test exercises the services but applies
  `bom_guardian.testing.TRANSFORM_SQL` (hand-written views) instead of invoking the real
  dbt project, so it is a *service-level* E2E test — it would not catch a broken dbt
  model/mart. H4 adds a true dbt-pipeline integration test alongside it.

## Hardening phase (H1–H10, post-M21)

Rigorous accuracy/validation/production-hardening pass over the completed M0–M21 build.

| # | Checkpoint | Status |
|---|------------|--------|
| H1 | Reconcile documentation and status | ✅ Complete |
| H2 | Enforce entity-disjoint ML evaluation | ✅ Complete |
| H3 | Strengthen defect-detection evaluation | ✅ Complete |
| H4 | True dbt end-to-end integration test | ✅ Complete |
| H5 | Complete/modernize the Snowflake execution path | ✅ Complete (implemented locally; external execution pending) |
| H6 | Add a configurable real AI provider | ✅ Complete (implemented + fake-client tested; external validation pending) |
| H7 | Role-based remediation authorization | ✅ Complete (demo auth; steward-gated decisions, authenticated actor recorded) |
| H8 | Verify GitHub Actions | ⬜ Not started |
| H9 | Verified application screenshots | ⬜ Not started |
| H10 | Final forensic audit | ⬜ Not started |

## In-progress work

- H8 next — verify the GitHub Actions workflows actually run green on github.com (not
  just locally); add a status badge only after a confirmed successful run and record the
  run URL here.

## Hardening results so far

- **H1** — reconciled docs; `evaluation/claim-verification.json` (21 claims with
  evidence + validation status). Retired the ML P=1.00/R=1.00 headline and the
  "verified live"/dbt-E2E overclaims.
- **H2** — entity-disjoint ML evaluation (connected-component grouping, runtime
  part-disjointness assertion, 5-seed dispersion). Honest numbers over 409 labeled
  pairs: candidate-gen recall 0.95; **LR P 0.962±0.010 / R 0.804±0.178 / F1 0.867±0.113**
  (recommended); GB P 0.769±0.431 / R 0.471±0.375 (high-variance). See
  `evaluation/entity_resolution/ml_eval.json` and `docs/model-card.md`.
- **H3** — fixed the generator so the pre-injection baseline is genuinely clean
  (active-only BOM components, active-only demand, contiguous revision windows),
  validated by `scripts/validate_clean_baseline.py` (only 5 allowlisted statistical
  conditions fire). New baseline-diff detection evaluation over **all 25 injected
  types**, attributed by subsystem: **SQL-detectable types recall 0.985 (194/197),
  precision ≥ 0.933** (conservative — unlinkable collateral counted as FP); per-type +
  per-difficulty + per-rule breakdown with explicit denominators; 3 duplicate types
  cross-referenced to ER, 2 documented as unevaluated. Artifacts
  `evaluation/data_quality/{clean_baseline,detection}_smoke.json`; 2 new tests lock in
  the clean-baseline property.
- **H4** — added `tests/end_to_end/test_dbt_pipeline.py`: a TRUE end-to-end test that
  invokes the real dbt project against a persistent DuckDB file, asserts all 11 core
  models and 7 marts build and populate, then runs the full quality → API →
  audited-approval loop against the dbt-built warehouse (fails if any dbt model/mart
  breaks). Renamed the fast `test_full_platform.py` case to `test_service_level_end_to_end`
  and documented that it uses `TRANSFORM_SQL`. Added a fixture-drift guard (dbt
  `dim_part` columns must match the `TRANSFORM_SQL` fixture) and documented the sync
  requirement in `src/bom_guardian/testing.py`.
- **H5** — completed/modernized the Snowflake path: a backend-agnostic `Warehouse`
  Protocol (`warehouse/base.py`), a `SnowflakeWarehouse` adapter (env-based config, no
  embedded creds, parameterized queries, `write_pandas` ingestion, table-existence +
  schema validation), the AI provider moved from legacy `SNOWFLAKE.CORTEX.COMPLETE` to
  **`AI_COMPLETE`** with a response schema, JSON validation, error handling,
  env-configurable model and latency capture, a `scripts/deploy_snowflake.py`
  (dry-run default; real execution needs credentials), scoped `SNOWFLAKE.CORTEX_USER`
  AI grant, and 12 fake-connection tests. **Still never executed against a live
  account — external execution pending.**
- **H6** — added `AnthropicAIProvider` (optional `anthropic` extra) on the official SDK:
  `output_config.format` JSON-schema constraint, JSON parse + shape check before the
  engine's full validation, SDK retry/timeout, refusal handling, env-configured key and
  model (default `claude-opus-4-8`), token + latency capture, abstention, no data-write
  path. Added a provider factory (`get_ai_provider`), `scripts/validate_real_ai_provider.py`
  (skips cleanly / exit 2 without a key — no fabricated artifact), and 7 fake-client
  tests + 1 integration test that skips without `ANTHROPIC_API_KEY`. **Never called
  against the real Anthropic API — external validation pending.**
- **H7** — added role-based authorization to the API (`api/app/auth.py`): an
  analyst/steward/admin role ladder, `get_principal` (Bearer-token → principal, 401 on
  missing/unknown token) applied at the router level to every business route, and
  `require_role(STEWARD)` on the approve / reject / request-evidence endpoints (403 for
  analysts). The recorded reviewer is now the **authenticated principal** — the
  `reviewer` field was removed from the request body, so a caller cannot spoof an actor.
  This is **demonstration auth** (static demo bearer tokens, overridable via
  `BOMG_DEMO_USERS`), clearly labeled as such and not an enterprise IdP integration; the
  frontend signs in as a steward via a demo token (`VITE_DEMO_TOKEN`). Added
  `tests/unit/test_authorization.py` (7 unit tests) and an API-level
  `test_authorization_enforcement` (401 unauthenticated, 401 unknown token, 403 analyst,
  200 analyst-read, issue never transitioned by denied attempts).

## Last successful commit

- `741153a` docs: publish complete BOM Guardian AI portfolio case study (M0–M21).
  The hardening phase (H1+) builds on top of it.

## Tests currently passing

- Python: 173 passed, 1 skipped — unit + integration + data-quality + API + E2E
  (`pytest`), ruff + mypy (`mypy src`) clean (measured this session; see `git log`).
- Frontend: 5 vitest tests, oxlint clean, `tsc -b` clean, production build succeeds.
- CI: workflows authored; **local equivalents of every job pass** (ruff, mypy, pytest,
  frontend lint/typecheck/test/build, dbt smoke pipeline). **GitHub Actions run status
  on github.com: not yet confirmed** — to be verified in H8.

## Known failures

- None locally.

## External integrations

**Configured / working:** GitHub push authentication (24 commits pushed to `main` over
HTTPS).

**Implemented locally, external execution pending (no credentials/resources):**
- **Snowflake** — provisioning scripts, role model, DuckDB-parity schema, `dbt`
  `snowflake` target, and Cortex/AI_COMPLETE provider are authored; **never executed
  against a live account**. Status: *implemented locally; external Snowflake execution
  pending.*
- **Power BI Desktop** — full source package (marts, semantic-model spec, DAX, theme,
  page specs); **no `.pbix` built or visually validated**. Status: *pending Desktop
  validation.*
- **Hosted AI provider (Anthropic/other)** — optional; real provider + validation
  script added in H6, marked *externally validated* only after a successful run.

## Next exact action

Proceed to H8 — inspect the GitHub Actions run history, fix any failing job, and confirm
a green run on github.com before adding a status badge or claiming CI passes; record the
run URL here.

## Honest completion percentage

**~92%** (revised during hardening). M0–M21 plus H1–H7 are built and locally tested:
ML-evaluation leakage (H2), DQ precision/recall (H3), the real-dbt E2E test (H4), the
Snowflake path (H5), the real AI provider (H6), and role-based authorization (H7) are all
addressed with tests. Remaining before any "complete" claim: confirmed green GitHub
Actions (H8), verified application screenshots (H9), the final forensic audit (H10), and
the external validations that need credentials/resources (live Snowflake deployment,
Power BI Desktop `.pbix`, a real AI-provider execution). Percentage will be re-derived
honestly in H10.
