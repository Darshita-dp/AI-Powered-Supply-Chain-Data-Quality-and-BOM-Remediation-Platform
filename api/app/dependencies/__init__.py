"""FastAPI dependency wiring (warehouse, AI provider, remediation engine)."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from bom_guardian.ai import DeterministicMockAIProvider, RemediationEngine
from bom_guardian.config import get_settings
from bom_guardian.warehouse import LocalWarehouse


@lru_cache
def _warehouse_singleton() -> LocalWarehouse:
    settings = get_settings()
    path = Path(settings.duckdb_path)
    if not path.exists():
        raise RuntimeError(
            f"Warehouse not found at {path}. Run `python scripts/run_local_pipeline.py` first."
        )
    return LocalWarehouse(path)


def get_warehouse() -> Iterator[LocalWarehouse]:
    yield _warehouse_singleton()


def get_remediation_engine() -> Iterator[RemediationEngine]:
    yield RemediationEngine(DeterministicMockAIProvider(), warehouse=_warehouse_singleton())
