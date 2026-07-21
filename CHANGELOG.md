# Changelog

All notable changes to BOM Guardian AI. Follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

No unreleased changes.

## [0.9.0] - 2026-07-20

First portfolio release. The platform is feature-complete and CI-verified for local,
reproducible operation (M0–M21 built, then hardened across checkpoints H1–H10). It is
**not** released as 1.0.0 because three external validations remain outstanding — see
*Known external validation gaps* below.

### Added

**Platform build (M0–M21)**

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
  threshold selection, model persistence, model card, measured comparison report,
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
- M15: FastAPI service — 24 versioned endpoints at the time of M15 (parts, issues +
  human decision workflow, BOM graph, scenarios, analytics), correlation IDs, structured
  errors, restricted CORS, OpenAPI, 13 API tests on real pipeline data. The service now
  exposes **29** operations after the hardening phase.
- M16: React remediation workbench — 8 surfaces over the live API (no mock data),
  cytoscape BOM explorer, approval workflow, scenario before/after, AI-governance
  dashboard; DuckDB thread-safety fix; 5 frontend tests.
- M17: Data Steward Copilot — allowlisted read-only tools, keyword classification,
  cited evidence, mutation refusal, insufficient-evidence handling, API endpoint +
  UI page, 8 tests.
- M18: Power BI package — 7 dbt analytics marts, semantic-model spec, 30+ DAX measures,
  theme, page specs with RLS/refresh/drill-through design, CSV fallback exporter;
  Desktop validation honestly marked pending.
- M19: CI/security — dbt smoke-pipeline CI job, docs link check, dependency review,
  optional manual Snowflake workflow, security threat model + AI governance docs.
- M20: end-to-end evaluation — 12-step E2E test, detection-recall report, measured
  smoke/demo benchmarks, measured profile counts incl. full profile (1,699,010 records /
  735 s generation).
  ⚠️ The M20 detection figure ("100% recall on 156 mapped injected defects across 17
  types") was recall-only, without a validated clean baseline and without precision. It
  is **superseded by H3** — do not quote it. Current figures: recall **0.985 (194/197)**,
  precision **≥ 0.933** over all 25 injected types.
- M21: portfolio packaging — final README with measured results and honest status
  table, data dictionary, API guide, limitations, demo script; hygiene audit clean
  (no TODOs, no secrets, all local doc links resolve).

**Hardening additions (H1–H10)**

- Backend-agnostic `Warehouse` protocol (`warehouse/base.py`) and a `SnowflakeWarehouse`
  adapter — env-based config with no embedded credentials, parameterized queries,
  `write_pandas` ingestion, table-existence and schema validation; plus
  `scripts/deploy_snowflake.py` (dry-run by default) and a scoped `SNOWFLAKE.CORTEX_USER`
  grant. (H5)
- `AnthropicAIProvider` (optional `anthropic` extra) on the official SDK —
  `output_config.format` JSON-schema constraint, JSON parse + shape check before the
  engine's full validation, SDK retry/timeout, refusal handling, env-configured key and
  model (default `claude-opus-4-8`), token + latency capture, abstention, and no
  data-write path. Added a `get_ai_provider` factory and
  `scripts/validate_real_ai_provider.py`, which skips cleanly (exit 2) without a key
  rather than fabricating an artifact. (H6)
- Role-based authorization layer (`api/app/auth.py`) with an analyst/steward/admin role
  ladder, `get_principal`, and `require_role`. (H7)
- `GET /api/v1/me` — reports the authenticated principal so the UI can display the actor
  a decision will be attributed to. (H9)
- `scripts/capture_screenshots.py` and `docs/screenshots/` — real Playwright captures of
  all 8 UI surfaces taken from the running application, with a manifest carrying captions
  and alt text. Exposed as `make screenshots` / `npm run screenshots`. (H9)
- `scripts/validate_clean_baseline.py` — asserts the pre-injection baseline is genuinely
  clean, so detection precision is measurable. (H3)
- `evaluation/claim-verification.json` — per-claim evidence and validation status for
  every published claim. (H1)
- `docs/final-verification-report.md` — forensic audit sorting every claim into
  verified-on-CI / tested-locally / externally-pending / not-implemented /
  manual-remaining, with explicit denominators. (H10)
- `tests/unit/test_release_metadata.py` — guards against version drift between
  `pyproject.toml`, `bom_guardian.__version__`, the changelog, and the release notes.

### Changed

- **Entity-resolution evaluation is now leakage-safe.** Candidate pairs form a graph over
  part ids, connected components become split groups, and train/val/test part-set
  disjointness is asserted at runtime. Re-measured over 5 split seeds on a 4,000-part
  profile (409 labeled duplicate pairs): candidate-generation recall 0.95; logistic
  regression P 0.962 ± 0.010 / R 0.804 ± 0.178 / F1 0.867 ± 0.113 (stable, recommended);
  gradient boosting P 0.769 ± 0.431 / R 0.471 ± 0.375 (high variance, not recommended at
  this scale). The earlier P=1.00/R=1.00 headline is **retired**. Candidate-generation
  recall is reported separately so model recall is not misread as end-to-end recall. (H2)
- **Generator fixes make the pre-injection baseline genuinely clean** — active-only BOM
  components and demand, contiguous non-overlapping revision windows — enabling a
  baseline-diff evaluation across all 25 injected types with subsystem attribution and
  explicit denominators. (H3)
- Snowflake AI provider moved from the legacy `SNOWFLAKE.CORTEX.COMPLETE` to
  **`AI_COMPLETE`**, with a response schema, JSON validation, error handling, a
  configurable model, and latency capture. (H5)
- Reviewer identity on a decision is now taken from the authenticated principal; the
  `reviewer` field was removed from the request body entirely. The Workbench's free-text
  "Reviewer name" input — a dead control after this change — was replaced with the
  signed-in identity from `GET /api/v1/me`. (H7, H9)
- Corrected the published endpoint count: the OpenAPI schema exposes **29** GET/POST
  operations, not the 25/26 previously documented. (H10)
- Removed `fetchPart`, dead code in the frontend API client. (H10)
- Package version set to 0.9.0 across `pyproject.toml`, `bom_guardian.__version__`, and
  the frontend package manifest; the API and OpenAPI schema report it.

### Security

- **Role-based authorization is enforced.** `get_principal` resolves a Bearer token to a
  principal (401 on a missing or unknown token) and is applied at the router level to
  every business route. Approve, reject, and request-evidence additionally require a
  steward or administrator (`require_role`, 403 for analysts). (H7)
- **Actors cannot be spoofed.** The recorded reviewer is the authenticated principal, and
  the request body carries no reviewer field. A denied attempt does not transition the
  issue (asserted by test). (H7)
- Authentication is **demonstration-grade and clearly labeled as such** — static demo
  bearer tokens overridable via `BOMG_DEMO_USERS`, not an enterprise IdP. There is no
  session management, token expiry, revocation, or rate limiting. The authorization logic
  is production-shaped; the credential source is not. (H7)
- AI governance guarantees unchanged and retested: no AI path can mutate data, grounding
  is enforced, abstention is a first-class outcome, every AI call is audited, and
  untrusted document content is flagged but never followed.

### Testing

- **A true dbt end-to-end test** (`tests/end_to_end/test_dbt_pipeline.py`) invokes the
  real dbt project against a persistent DuckDB file, verifies all 11 core models and 7
  marts build and populate, then runs the full engine + API + audited-approval loop
  against the dbt-built warehouse. The fast test was relabeled *service-level*, and a
  fixture-drift guard prevents `TRANSFORM_SQL` from silently diverging from the dbt
  models. (H4)
- **GitHub Actions is genuinely green** — it had never passed before this release. The
  python job installed `.[dev,api,ml]`, but the document-intelligence tests import
  `reportlab`/`pypdf` from the `docs-ai` extra, so pytest aborted during *collection*
  with exit code 2; the suite passed locally only because that machine had every extra
  installed. A latent `ruff format --check` failure on 8 files was fixed at the same
  time. The job now installs `.[dev,api,ml,docs-ai,dbt]`, asserts dbt is importable so
  the real dbt E2E test cannot silently skip, and runs `pytest -rs` to surface skips. (H8)
- Suite grew from 136 to **182 passing tests (1 skipped)** at 93% line coverage, adding
  connected-component / entity-disjointness / leak-rejection / multi-seed tests (H2),
  clean-baseline tests (H3), 12 Snowflake fake-connection tests (H5), 7 Anthropic
  fake-client tests plus a skipped-without-key integration test (H6), 8 authorization
  tests (H7), and 8 screenshot-harness regression tests (H9).

### Documentation

- Reconciled stale and contradictory status wording repository-wide and introduced
  per-claim evidence tracking. Retired the "no entity leakage" claim and the
  P=1.00/R=1.00 headline; relabeled the M20 E2E test as service-level; clarified
  detection recall; marked screenshots and CI status explicitly pending at the time. (H1)
- Detection evaluation now documents precision alongside recall, splits false positives
  into collateral versus spurious, and records per-type, per-difficulty, and per-rule
  breakdowns with explicit denominators. Two duplicate-related types are documented as
  unevaluated by SQL and cross-referenced to entity resolution. (H3)
- Corrected two stale claims that contradicted the shipped code: `docs/api-guide.md`
  still said "No authentication is implemented" and `docs/limitations.md` still claimed
  reviewer identity was self-declared — both superseded by H7. Also annotated a
  superseded "100% recall" figure and stale test counts in historical status entries, and
  refreshed the `api` and `tests` entries in the claim inventory. (H10)
- Added `docs/screenshots/README.md` explaining how captures are produced and why they
  are real rather than fixtures, and a README screenshot gallery with alt text and
  captions. (H9)

### Known external validation gaps

These are the reason this release is **0.9.0 and not 1.0.0**. Each is implemented and
unit-tested with fakes, but has never touched the real external system:

- **Snowflake** — the adapter, provisioning scripts, role model, dbt `snowflake` target,
  and Cortex `AI_COMPLETE` provider have **never been executed against a live account**
  (no credentials). No `evaluation/snowflake/` artifacts exist.
- **Anthropic provider** — **never called against the real API** (no key).
  `evaluation/ai/real_provider_validation.json` does not exist, and the integration test
  skips.
- **Power BI Desktop** — the full source package exists, but **no `.pbix`/`.pbip` has
  been built or visually validated**; the DAX has never executed in a live model.

[Unreleased]: https://github.com/Darshita-dp/AI-Powered-Supply-Chain-Data-Quality-and-BOM-Remediation-Platform/compare/v0.9.0...HEAD
[0.9.0]: https://github.com/Darshita-dp/AI-Powered-Supply-Chain-Data-Quality-and-BOM-Remediation-Platform/releases/tag/v0.9.0
