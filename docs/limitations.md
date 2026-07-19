# Limitations — BOM Guardian AI

An honest list of what this project does **not** do or prove.

## Data and scale

- **All data is synthetic.** Distributions are plausible but simplified; real ERP
  master data has failure modes not modeled here (multilingual text, unit conversions,
  free-text abuse, decades of schema drift).
- **Full profile (1.7M records) was generated and measured, but the downstream
  pipeline stages (ingest, dbt, rules, ER) have only been run at smoke (~14k) and demo
  (~248k) scale.** Published benchmarks state their profile explicitly.
- Ingestion computes per-row hashes in Python (pandas apply) — the demo profile ingests
  in ~19s, but this would need vectorizing/warehouse-native hashing at full scale.

## Machine learning

- ER models are trained and evaluated on **synthetic duplicates**; recall/precision on
  smoke-scale data has wide confidence intervals (~6 positives in the held-out test
  split). Metrics would need re-estimation on larger labeled sets before any real use.
- No semantic/embedding matching; hard multilingual or synonym duplicates will be missed.
- Golden-record survivorship accuracy has unit-test coverage but no large ground-truth
  field-level accuracy report yet.

## Platform

- **Authentication is demonstration-grade, not production IAM.** Role-based
  authorization *is* enforced (analyst/steward/admin; approve/reject/request-evidence
  require steward or admin; the recorded actor is the authenticated principal, never a
  body-supplied name). But identities come from static demo bearer tokens in
  `api/app/auth.py`, not an SSO/OIDC provider, and there is no session management, token
  expiry, revocation, or rate limiting. A real deployment must swap the token store for a
  corporate IdP; the authorization checks themselves carry over.
- **Snowflake is scripted but has never been deployed** (no account/credentials).
  All Snowflake artifacts are labeled "pending external validation."
- **Snowflake Cortex AI provider is implemented but never executed** against a live
  account; only the deterministic mock provider is tested.
- **Power BI**: full source package exists; **no `.pbix` was built or visually
  validated** (Power BI Desktop was not operated). DAX is authored but has not executed
  in a live model.
- The copilot uses deterministic keyword classification, not an LLM; unusual phrasings
  fall to the "unsupported" path by design.
- Local API uses a single DuckDB connection guarded by a lock — fine for a demo, not a
  concurrency story for production.
- Scenario simulation estimates exposure; it does not re-run MRP or costing.
- Issue lifecycle implements DETECTED → PENDING_REVIEW → APPROVED/REJECTED with audit;
  the extended ENRICHED/PRIORITIZED/SIMULATED/VALIDATED/CLOSED states exist in the
  transition design but only the review-decision transitions are exercised by the UI.

## Process

- Reviewer decisions in evaluations are **simulated** (made by tests), so acceptance
  rates are demonstrations of the mechanism, not human-behavior measurements.
- CI workflows are authored and their local equivalents pass; the GitHub Actions run
  history on the repository is the source of truth for CI status.
