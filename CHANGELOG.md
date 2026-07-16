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
