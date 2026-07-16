# Architecture Decision Records — BOM Guardian AI

Brief ADRs; newest at the bottom. Format: Decision / Context / Alternatives / Selected / Consequences.

---

## ADR-001: DuckDB as the mandatory local warehouse fallback

- **Context:** Snowflake is the target platform but requires a paid account; tests and CI
  must run for free and offline.
- **Alternatives:** Postgres in Docker (heavier, weaker analytical SQL parity),
  SQLite (poor analytical SQL), Snowflake-only (blocks CI).
- **Selected:** DuckDB for all local pipeline/dbt/test execution; Snowflake DDL kept
  adapter-separated in `warehouse/snowflake/`.
- **Consequences:** SQL and dbt macros must stay adapter-safe; Snowflake deployment is
  validated separately and its status reported honestly.

## ADR-002: Interpretable-first entity resolution

- **Context:** Wrong part/supplier merges are operationally damaging; stewards must be
  able to see why a match was proposed.
- **Alternatives:** Sentence-transformer embeddings first; deep pairwise models.
- **Selected:** Weighted deterministic baseline → logistic regression → gradient
  boosting, all over explicit similarity features; optional semantic similarity as one
  feature, never the sole decider. Precision-favored thresholds; abstain band; no auto-merge.
- **Consequences:** Slightly lower recall ceiling than embedding-heavy approaches, but
  every match carries human-readable evidence.

## ADR-003: AI behind a provider interface with a deterministic mock

- **Context:** Core tests must not require paid AI APIs; AI output must be governed.
- **Alternatives:** Direct Anthropic SDK calls; skipping AI in tests.
- **Selected:** `AIProvider` interface with `DeterministicMockAIProvider` (default in
  tests), `SnowflakeCortexAIProvider` (target), optional Anthropic via config. All output
  schema-validated (Pydantic); abstention supported; providers have no write path to
  golden state.
- **Consequences:** CI is fully deterministic; real-provider behavior is validated only
  when credentials exist and is labeled accordingly.

## ADR-004: Ground truth isolated from model inputs

- **Context:** Injected-defect labels enable honest evaluation but would leak if
  co-located with pipeline data.
- **Alternatives:** Store labels as columns on the affected tables.
- **Selected:** Separate `data_generator/ground_truth/` outputs and a separate warehouse
  schema, consumed only by evaluation code.
- **Consequences:** Evaluation reports are credible; detection/ER metrics are real
  measurements, not self-confirming.

## ADR-005: Simulation never mutates baseline

- **Context:** Stewards need before/after previews of merges and corrections without risk.
- **Alternatives:** Apply-then-rollback; branching table copies per scenario.
- **Selected:** Scenario results are computed in memory / persisted to dedicated
  scenario tables keyed by scenario ID; golden and core tables are read-only to the
  simulator and the AI engine.
- **Consequences:** Slightly more computation per scenario; zero risk of accidental
  master-data corruption; approvals remain the only mutation path, and they are audited.

## ADR-006: Python 3.13 as the local interpreter

- **Context:** The spec targets "Python 3.12 or a currently supported compatible
  version"; the build machine has Python 3.13.
- **Alternatives:** Install 3.12 side-by-side.
- **Selected:** Develop against 3.13; keep `requires-python = ">=3.12"` so both work;
  CI matrix will exercise 3.12.
- **Consequences:** Dependencies must support 3.13 (all planned libraries do).
