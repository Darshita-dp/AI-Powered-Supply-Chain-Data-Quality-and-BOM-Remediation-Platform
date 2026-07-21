# BOM Guardian AI v0.9.0

**Release date:** 2026-07-20 · **Classification:** portfolio release (prerelease) ·
**Not production-ready** — see *Validation status* and *Known limitations*.

## Release summary

This is the first stable portfolio release of BOM Guardian AI — a locally reproducible,
AI-assisted supply-chain data-quality and BOM-remediation platform.

It detects master-data and bill-of-materials defects across simulated ERP source systems,
resolves duplicate parts into explainable golden records, computes each defect's
downstream **blast radius** (the "Quality Impact Twin"), and routes governed AI
remediation proposals through a role-gated human-approval workflow — end to end, on a
laptop, with no cloud account required.

Everything runs on DuckDB and a deterministic mock AI provider by default, so a reviewer
can clone the repository and reproduce every published number. Snowflake and a real
hosted AI provider are implemented as optional backends behind the same interfaces.

The version is **0.9.0 rather than 1.0.0** deliberately: three external validations
remain outstanding (live Snowflake, a real Anthropic API execution, and a Power BI
Desktop report). Nothing in this release claims those have been done.

## Major capabilities

| Capability | What it does |
|---|---|
| **Synthetic ERP generator** | 22 interrelated datasets (part master, aliases, suppliers, plants, BOM headers/components, revisions, ECOs, inventory, POs, demand, cost/lead-time history, quotes) across smoke/demo/full profiles with deterministic seeds and referential-integrity validation |
| **Controlled defect injection + ground truth** | 25 defect types at easy/medium/hard difficulty, with labels written to an isolated `ground_truth/` directory that never feeds model inputs |
| **Auditable ingestion** | Audit columns (batch id, file/row SHA-256 hashes, sequence, status), file-hash idempotency, null-PK rejection to `ops.rejected_records`, batch/file audit tables |
| **dbt warehouse transformations** | 22 sources → 10 staging views → 11 core dimensions/facts → 7 analytics marts, with adapter-safe macros for DuckDB and Snowflake and 28 schema tests |
| **49-rule data-quality engine** | Rules across 9 domains with per-rule failure isolation, issue + evidence persistence, and transparent entity/BOM/enterprise scoring |
| **Entity resolution** | Blocking + 11 interpretable features; a weighted explainable baseline plus logistic-regression and gradient-boosting models, evaluated on entity-disjoint splits |
| **Field-level golden-record survivorship** | Per-field selection scored on source reliability, recency, and cross-source agreement, with full reversible lineage including alternatives and confidence |
| **BOM graph intelligence** | Cycle, self-reference, and orphan detection; depth, reverse dependencies, path tracing, expansion, centrality, criticality, and supplier concentration |
| **Quality Impact Twin** | Blast-radius exposure (affected assemblies, demand, inventory and open-PO value, suppliers, plants, operational priority) plus merge / field-correction / component-replacement counterfactuals with before-after diffs and new-conflict warnings — simulations never mutate baseline data |
| **Governed AI remediation** | Provider interface with a schema-constrained proposal that contains no approve action and cannot set `human_review_required` false; grounding validation rejects evidence outside the supplied bundle; abstention is first-class; every call is audited |
| **Human approval workflow** | Lifecycle-guarded decisions (409 on invalid transition) with a full decision audit trail |
| **Role-based demonstration authorization** | Analyst / steward / admin ladder; approve, reject, and request-evidence require steward or above; the recorded actor is the authenticated principal and cannot be supplied by the client |
| **FastAPI backend** | 29 versioned `/api/v1` operations with pagination, allowlisted sorting, correlation IDs, structured errors without stack traces, restricted CORS, and OpenAPI |
| **React workbench** | 8 surfaces over live API data (no mock data path), including a Cytoscape BOM explorer, approval workflow, scenario before/after, and an AI-governance dashboard |
| **Power BI analytical source package** | 7 marts, semantic-model spec, 30+ DAX measures, theme, and page specs with RLS/refresh/drill-through design, plus a CSV fallback exporter |
| **GitHub Actions** | Python 3.12 + 3.13 (lint, format, types, full test suite including the real dbt E2E), frontend (lint/typecheck/test/build), dbt smoke pipeline, docs-link check, and gitleaks secret scanning |
| **Real application screenshots** | All 8 surfaces captured from the running app by a reproducible Playwright script that asserts live API values appear in the DOM before saving |

## Verified results

All figures below come from committed evaluation artifacts and the
[final verification report](docs/final-verification-report.md). Data is synthetic and
seeded (seed 20260716); regenerate with `scripts/evaluate_detection.py` and
`scripts/evaluate_entity_resolution.py`.

### Defect detection — smoke profile, against a validated clean baseline

| Metric | Value | Denominator / limitation |
|---|---|---|
| Recall (SQL-detectable types) | **0.9848** | 194 detected of **197 labeled defects** |
| Precision (injection-caused) | **0.9333** | 184 true positives of 210 new detections; 14 spurious |
| Coverage | **20 of 25** injected types evaluated here | The other 5 are duplicate-type defects measured by entity resolution instead |

> Precision is a **conservative lower bound**. Any new detection whose entity is not
> itself a ground-truth record counts as a false positive, but these are dominated by
> *unlinkable collateral* — the same real, injection-caused defect surfacing on a related
> record the exact-id matcher cannot link (an obsolete part used in several active BOMs,
> a cycle's partner edge, a price conflict bleeding into that supplier's quote).

### Entity resolution — entity-disjoint splits, 5 seeds

| Metric | Value | Denominator / limitation |
|---|---|---|
| Candidate-generation recall (blocking) | **0.9511** | 389 of **409 labeled duplicate pairs**, 4,000 parts |
| Logistic regression *(recommended)* | **P 0.9623 ± 0.0097 · R 0.8041 ± 0.1785 · F1 0.8670 ± 0.1133** | Model recall is *conditional on candidate generation* |
| Gradient boosting *(not recommended)* | P 0.7690 ± 0.4308 · R 0.4714 ± 0.3746 | High variance at this scale |

> **End-to-end duplicate recall is roughly 0.95 × 0.80 ≈ 0.76**, not 0.80. Splits are
> connected-component entity-disjoint with runtime assertions. An earlier P=1.00/R=1.00
> headline was an artifact of entity leakage and has been retired.

### Scale and performance

| Metric | Value | Limitation |
|---|---|---|
| Generated records — smoke / demo / full | 13,882 / 247,881 / **1,699,010** | Full-profile numbers cover **generation only** (734.9 s); downstream stages were measured at smoke/demo scale |
| 49 rules over the demo profile (248k records) | 0.9 s | Single-machine measurement |
| API list endpoints | ~10 ms | Local DuckDB, single connection |

### Test and pipeline results

| Check | Result |
|---|---|
| Python test suite | **182 passed, 1 skipped**, 93% line coverage |
| Frontend | 5 vitest tests; oxlint, `tsc -b`, and production build clean |
| Lint / format / types | `ruff check`, `ruff format --check`, `mypy src` all clean |
| Real dbt smoke pipeline | exit 0 — staging+core `PASS=47 ERROR=0`, marts `PASS=7 ERROR=0`, 49 rules executed with 0 failures |

The single skip is the Anthropic integration test, which requires `ANTHROPIC_API_KEY`.

## Validation status

### Verified through GitHub Actions

Executed on GitHub-hosted runners; run URLs recorded in
[`PROJECT_STATUS.md`](PROJECT_STATUS.md).

- `python (3.12)` and `python (3.13)` — ruff, `ruff format --check`, `mypy src`, and the
  full pytest suite **including the real dbt end-to-end test**
- `frontend` — lint, typecheck, tests, production build
- `dbt` — the real local pipeline: generate → inject → ingest → dbt build → rules → marts
- `docs-links` — markdown link check
- `secrets` — gitleaks scan over full history

(`dependency-review` shows as skipped by design; it is gated on pull requests.)

### Tested locally

Reproduced in a clean virtualenv provisioned exactly as CI does. Covers all measured
metrics above, baseline-immutability assertions, authorization enforcement (401/403 and
no state transition on denial), AI-governance guarantees, and the screenshot capture.

### Implemented but externally unvalidated

| Capability | Missing evidence |
|---|---|
| Snowflake warehouse, provisioning, deploy path, and Cortex `AI_COMPLETE` provider | Never executed against a live account; no credentials; no `evaluation/snowflake/` artifacts exist |
| Anthropic AI provider | Never called against the real API; `evaluation/ai/real_provider_validation.json` does not exist |
| Power BI report | No `.pbix`/`.pbip` exists; DAX has never executed in a live model |

### Manual work remaining

1. Run `python scripts/deploy_snowflake.py --execute` against a real Snowflake account,
   then run the pipeline on the `snowflake` dbt target.
2. Set `ANTHROPIC_API_KEY` and run `python scripts/validate_real_ai_provider.py` to
   produce the validation artifact.
3. Build the model in Power BI Desktop per `powerbi/BUILD_POWER_BI.md` and publish the
   report.
4. Re-run `make screenshots` after any material UI change.

## Known limitations

- **Synthetic data only.** Every part, supplier, price, and document is generated. No
  real company, supplier, or personal data appears anywhere, and all quality metrics are
  measured against injected, labeled defects.
- **Demonstration authentication, not enterprise SSO.** Role-based authorization *is*
  enforced, but identities come from static demo bearer tokens — there is no OIDC/SAML
  integration, session management, token expiry, revocation, or rate limiting.
- **Snowflake deployment pending.** Implemented and fake-connection tested; never run
  against a live account.
- **Anthropic live validation pending.** Implemented and fake-client tested; never called
  with a real API key.
- **Power BI Desktop report pending.** Source package complete; no `.pbix` built or
  visually validated.
- **No production deployment claim.** This is a portfolio release. It has not been
  deployed, load-tested, security-audited by a third party, or run against real data.
  The local API uses a single lock-guarded DuckDB connection, which is not a concurrency
  story for production, and API SQL uses an escaping helper with allowlisted sort columns
  rather than bound parameters (documented in [`docs/security-model.md`](docs/security-model.md)).
- Entity-resolution metrics come from a single 4,000-part synthetic profile and would
  need re-estimation on larger labeled sets before real use.
- The Copilot uses deterministic keyword classification, not an LLM; unusual phrasings
  fall to an explicit "insufficient evidence" path by design.

## Running the release

No cloud account needed — everything runs locally.

```bash
git clone https://github.com/Darshita-dp/AI-Powered-Supply-Chain-Data-Quality-and-BOM-Remediation-Platform.git
cd AI-Powered-Supply-Chain-Data-Quality-and-BOM-Remediation-Platform
python -m venv .venv && . .venv/Scripts/activate     # Windows Git Bash
pip install -e ".[dev,api,ml,docs-ai,dbt]"

python scripts/run_local_pipeline.py                 # generate → inject → ingest → dbt → rules → marts
uvicorn api.app.main:app --port 8000                 # API (terminal 1)
cd frontend && npm install && npm run dev            # UI  (terminal 2) → http://localhost:5173
```

The API requires a bearer token; the demo credentials are documented in
[`docs/api-guide.md`](docs/api-guide.md):

```bash
curl -H "Authorization: Bearer demo-steward-token" http://127.0.0.1:8000/api/v1/issues
```

Verification and evaluation:

```bash
ruff check . && ruff format --check . && mypy src && pytest
cd frontend && npm run lint && npm run typecheck && npm test -- --run && npm run build

python scripts/evaluate_detection.py                 # detection precision/recall
python scripts/evaluate_entity_resolution.py         # ER metrics
python scripts/benchmark.py                          # performance
make screenshots                                     # real UI captures (needs Playwright)
```

## Further reading

- [Final verification report](docs/final-verification-report.md) — what is CI-verified
  versus locally tested versus externally pending
- [Project status](PROJECT_STATUS.md) — milestone and hardening detail
- [Changelog](CHANGELOG.md) — full 0.9.0 entry
- [Limitations](docs/limitations.md) — what this project does **not** prove
- [Security model](docs/security-model.md) · [AI governance](docs/ai-governance.md)

## License

[MIT](LICENSE)
