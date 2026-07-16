# Changelog

All notable changes to BOM Guardian AI. Follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

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
