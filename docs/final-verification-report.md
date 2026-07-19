# Final Verification Report — BOM Guardian AI

**Audit date:** 2026-07-19 · **Audited commit:** `c4c8bbc` (+ this report) ·
**Auditor:** final forensic pass (hardening checkpoint H10)

This report states what is actually true about this repository. Every claim below is
tied to a command, artifact, test, or CI run that was executed — not to intent. Where
something has *not* been done, it says so plainly.

---

## 1. Verification tiers

Claims are sorted into five tiers. Nothing is promoted a tier without evidence.

| Tier | Meaning |
|---|---|
| **A — Verified through GitHub Actions** | Executed on GitHub-hosted runners; run URL recorded |
| **B — Implemented and tested locally** | Runs and passes here; not exercised on external infrastructure |
| **C — Implemented, external validation pending** | Code exists and is unit-tested with fakes, but has never touched the real external system |
| **D — Not implemented** | Does not exist |
| **E — Manual work remaining** | Requires a human with credentials/software |

---

## 2. Tier A — Verified through GitHub Actions

CI run **[29671853670](https://github.com/Darshita-dp/AI-Powered-Supply-Chain-Data-Quality-and-BOM-Remediation-Platform/actions/runs/29671853670)**
on commit `c4c8bbc`, conclusion **success**. (Previous green run:
[29670834422](https://github.com/Darshita-dp/AI-Powered-Supply-Chain-Data-Quality-and-BOM-Remediation-Platform/actions/runs/29670834422)
on `13fa952`.)

| Job | Result | What it proves |
|---|---|---|
| `python (3.12)` | success | ruff check, `ruff format --check`, `mypy src`, full pytest **including the real dbt end-to-end test** |
| `python (3.13)` | success | same, on a second interpreter |
| `frontend` | success | oxlint, `tsc -b`, vitest, production build |
| `dbt` | success | the real local pipeline: generate → inject → ingest → **dbt build** → rules → marts |
| `docs-links` | success | lychee link check over README, docs/, powerbi/ |
| `secrets` | success | gitleaks scan over full history (`fetch-depth: 0`) |
| `dependency-review` | *skipped* | by design — gated on `github.event_name == 'pull_request'` |

**Honesty note:** before H8, GitHub Actions had **never** passed. Every run failed
because the python job installed `.[dev,api,ml]` while
`tests/integration/test_document_intelligence.py` needs `reportlab`/`pypdf` from the
`docs-ai` extra — pytest aborted during *collection* with exit code 2. The suite passed
locally only because this machine had every extra installed. A second latent failure
(`ruff format --check` rejecting 8 files) was fixed in the same checkpoint.

---

## 3. Tier B — Implemented and tested locally

All commands below were run in a **clean virtualenv** provisioned exactly as CI does
(`pip install -e ".[dev,api,ml,docs-ai,dbt]"`).

| Check | Command | Result |
|---|---|---|
| Lint | `ruff check .` | All checks passed |
| Format | `ruff format --check .` | 105 files already formatted |
| Types | `mypy src` | no issues in 41 source files |
| Tests | `pytest` | **182 passed, 1 skipped** (skip = no `ANTHROPIC_API_KEY`), coverage 93% |
| Frontend lint / types / tests / build | `npm run lint`, `typecheck`, `test -- --run`, `build` | clean · clean · 5 passed · built |
| Real dbt smoke pipeline | `python scripts/run_local_pipeline.py --profile smoke` | exit 0 · staging+core `PASS=47 ERROR=0` · marts `PASS=7 ERROR=0` · 49 rules executed, 0 failed, 1,097 issues created |
| Markdown links | link check over all 24 tracked `.md` files | all local links resolve |

### Headline metrics — with denominators

Regenerate with `scripts/evaluate_detection.py` and `scripts/evaluate_entity_resolution.py`.

**Defect detection** ([`detection_smoke.json`](../evaluation/data_quality/detection_smoke.json)),
smoke profile, seed 20260716, measured against a *validated clean baseline*
([`clean_baseline_smoke.json`](../evaluation/data_quality/clean_baseline_smoke.json)):

| Metric | Value | Denominator / caveat |
|---|---|---|
| Recall (SQL-detectable types) | **0.9848** | 194 detected of **197 labeled defects** |
| Precision (injection-caused) | **0.9333** | 184 true positives of 210 new detections; 14 spurious |
| Injected defect types | 25 total | **20 SQL-detectable** and evaluated here |
| Types not evaluated by SQL | 5 | `exact_duplicate_part`, `fuzzy_duplicate_part`, `conflicting_mpn`, `conflicting_part_descriptions`, `duplicate_supplier` — these are entity-resolution concerns, measured separately below |

> Precision is a **conservative lower bound**. Any new detection whose entity is not
> itself a ground-truth record counts as a false positive, but on inspection these are
> dominated by *unlinkable collateral* — the same real, injection-caused defect surfacing
> on a related record the exact-id matcher cannot link (an obsolete part used in several
> active BOMs, a cycle's partner edge, a price conflict bleeding into that supplier's
> quote). Genuinely spurious flags are rarer than 14 suggests.

**Entity resolution** ([`ml_eval.json`](../evaluation/entity_resolution/ml_eval.json)),
4,000 parts, **409 labeled duplicate pairs**, 5 split seeds `[1,7,13,21,31]`,
**connected-component entity-disjoint** splits (asserted at runtime):

| Metric | Value | Caveat |
|---|---|---|
| Candidate-generation recall (blocking) | **0.9511** | 389 of 409 pairs produced as candidates |
| Logistic regression | **P 0.9623 ± 0.0097 · R 0.8041 ± 0.1785 · F1 0.8670 ± 0.1133** | recommended; recall is *conditional on candidate generation* |
| Gradient boosting | P 0.7690 ± 0.4308 · R 0.4714 ± 0.3746 | high variance at this scale — **not recommended** |

> End-to-end duplicate recall = candidate-generation recall × model recall, i.e. roughly
> **0.95 × 0.80 ≈ 0.76**, not 0.80. The earlier P=1.00/R=1.00 headline was an artifact of
> entity leakage across splits and was retired in H2.

**Scale** ([`profile_counts.json`](../evaluation/performance/profile_counts.json)):
smoke **13,882** records (with injection) · demo **247,881** · full **1,699,010**
(generation 734.9 s). Full-profile numbers cover **generation only** — downstream stages
were measured at smoke/demo scale.

### Security and authorization (locally tested)

- Role ladder analyst / steward / admin; `require_role(STEWARD)` gates
  approve / reject / request-evidence. Unauthenticated → 401, insufficient role → 403,
  and the issue is **not** transitioned by a denied attempt (asserted).
- The recorded reviewer is the **authenticated principal**; the `reviewer` field was
  removed from the request body entirely, so an actor cannot be spoofed.
- 8 authorization tests (`tests/unit/test_authorization.py` + an API-level enforcement
  test).

### Screenshots

All 8 surfaces captured from the **running application** by
`scripts/capture_screenshots.py` (real pipeline → FastAPI → Vite → Playwright), stored in
[`docs/screenshots/`](screenshots/) with a manifest carrying captions and alt text.
The script asserts live API values appear in the rendered DOM before saving and exits
non-zero rather than emitting placeholders. 8 harness regression tests guard it.

---

## 4. Tier C — Implemented, external validation pending

| Capability | State | Missing evidence |
|---|---|---|
| **Snowflake warehouse + deployment** | `SnowflakeWarehouse` adapter (env config, parameterized queries, `write_pandas`), provisioning scripts, role model, dbt `snowflake` target, `scripts/deploy_snowflake.py` (dry-run default), 12 fake-connection tests | **Never executed against a live Snowflake account.** No credentials. No `evaluation/snowflake/` artifacts exist |
| **Snowflake Cortex AI provider** | Modernized to `AI_COMPLETE` with response schema, JSON validation, error handling, configurable model, latency capture; a test asserts the legacy `CORTEX.COMPLETE` is *not* used | Never called against live Cortex |
| **Anthropic AI provider** | `AnthropicAIProvider` on the official SDK: `output_config.format` JSON-schema constraint, grounding validation, SDK retry/timeout, refusal handling, token/latency audit, abstention, no data-write path; 7 fake-client tests | **Never called against the real API.** `evaluation/ai/real_provider_validation.json` does not exist; `scripts/validate_real_ai_provider.py` skips (exit 2) without a key, and the integration test skips — confirmed in this run's skip report |
| **Power BI report** | 7 dbt analytics marts, semantic-model spec, 30+ DAX measures, theme, page specs with RLS/refresh/drill-through design, CSV fallback exporter | **No `.pbix` exists** anywhere in the repo (verified by filesystem search). DAX has never executed in a live model |

---

## 5. Tier D / E — Not implemented, and manual work remaining

**Not implemented (by design, documented):**
- No production IAM — authentication is demonstration-grade (static demo bearer tokens);
  no SSO/OIDC, session management, token expiry, revocation, or rate limiting.
- No semantic/embedding entity matching (interpretable features only).
- Copilot uses deterministic keyword classification, not an LLM.
- No automatic retraining from reviewer feedback (deliberate governance choice).

**Manual work remaining for the repository owner:**
1. Run `scripts/deploy_snowflake.py --execute` against a real Snowflake account, then
   re-run the pipeline on the `snowflake` target.
2. Set `ANTHROPIC_API_KEY` and run `python scripts/validate_real_ai_provider.py` to
   produce `evaluation/ai/real_provider_validation.json`, then flip the
   `real-ai-provider` claim to *measured*.
3. Open Power BI Desktop, build the model per `powerbi/BUILD_POWER_BI.md`, and commit or
   publish the `.pbix`.
4. Re-run `make screenshots` whenever the UI changes materially.

---

## 6. Findings from this audit (and what was done)

| # | Finding | Action |
|---|---|---|
| 1 | `docs/api-guide.md` still said **"No authentication is implemented"** — stale since H7 and directly contradicted by the shipped authorization layer | Corrected to describe demonstration-grade auth + role enforcement |
| 2 | `docs/limitations.md` still claimed **"No authentication or authorization — reviewer identity is self-declared"** | Rewritten to state what is enforced and precisely what is missing (IdP, sessions, expiry, rate limits) |
| 3 | Endpoint count published as 25/26; the OpenAPI schema actually exposes **29** GET/POST operations (guide rows group several paths) | README and API guide corrected to 29, with a note on how it is counted |
| 4 | `fetchPart` exported from the frontend API client but never used — dead code | Removed; typecheck and build re-verified |
| 5 | Workbench "Reviewer name" input had been made meaningless by H7 (a dead control implying a typed name is recorded) | Fixed in H9: replaced with the authenticated identity from a new `GET /api/v1/me` |

**Clean scans (no findings):** no `TODO`/`FIXME`/`XXX`/`HACK` markers in tracked source;
no `NotImplementedError`/stub/placeholder implementations (all "placeholder" hits are
legitimate HTML input attributes); no hard-coded secrets, API keys, or private keys (the
only credential-shaped literal is the documented `demo-steward-token`); no generated or
local artifacts tracked (no `.duckdb`, `node_modules`, `.env`, `data/generated`, dbt
`target/`, `__pycache__`); no frontend mock/fixture data outside tests — every page reads
the API; all 24 markdown files' local links resolve; legacy `SNOWFLAKE.CORTEX.COMPLETE`
appears only in docs describing its replacement and in a test asserting it is unused.

**Known, documented, and accepted:** API SQL is built with f-strings using a `_safe()`
escaping helper plus allowlisted sort columns, bounded pagination, and regex-constrained
sort direction — **not** bound parameters. This is a real deviation from best practice on
the local DuckDB trust boundary and is recorded in `docs/security-model.md`; a Snowflake
deployment should move to bound parameters throughout.

**Test-fixture drift:** `tests/end_to_end/test_dbt_pipeline.py::_assert_no_fixture_drift`
fails the build if the hand-written `TRANSFORM_SQL` fixture diverges from the real dbt
`dim_part` model, so the fast service-level test cannot silently drift from production
transformations.

---

## 7. Honest completion assessment

### What a reviewer can trust today

The data platform is real and reproducible end to end on a laptop: 22 synthetic ERP
datasets, 25 controlled defect types with isolated ground truth, audited ingestion, a
real dbt star schema plus 7 marts, a 49-rule quality engine measured against a validated
clean baseline, leakage-safe entity resolution, blast-radius impact with counterfactual
simulation, a governed AI proposal path that cannot mutate data, role-gated human
approval with a full audit trail, and a React workbench proven by real screenshots — all
of it verified green on GitHub Actions across two Python versions.

### Completion: **93%**

Reached by scope, not sentiment. Everything that can be built and proven without external
credentials is done and verified (M0–M21 plus H1–H10, CI green, screenshots captured).
The remaining ~7% is work that **cannot** be completed in this environment because it
requires resources this project does not have:

| Outstanding | Weight |
|---|---|
| Snowflake never executed against a real account | ~3% |
| Anthropic provider never run with a real key | ~2% |
| Power BI Desktop `.pbix` never built or visually validated | ~2% |

**This project is deliberately not called 100% complete.** Per the hardening
requirements, that label is withheld while any of the following hold — and three still
do:

- ❌ Snowflake has not been executed against a real account
- ❌ The Anthropic provider has not been successfully run with credentials
- ❌ Power BI Desktop has not produced and validated the final report
- ✅ Screenshot capture is complete (8/8 surfaces, real captures)
- ✅ GitHub Actions is green (run 29671853670)

---

## 8. Reproducing this audit

```bash
python -m venv .venv && . .venv/Scripts/activate       # Windows Git Bash
pip install -e ".[dev,api,ml,docs-ai,dbt]"

ruff check . && ruff format --check . && mypy src && pytest
python scripts/run_local_pipeline.py --profile smoke
cd frontend && npm ci && npm run lint && npm run typecheck && npm test -- --run && npm run build
```

Per-claim evidence and validation status for every published claim:
[`evaluation/claim-verification.json`](../evaluation/claim-verification.json).
