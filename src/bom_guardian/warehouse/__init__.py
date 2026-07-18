"""Warehouse backends: DuckDB local (default) and Snowflake target, one interface."""

from __future__ import annotations

from bom_guardian.warehouse.base import SCHEMAS, Warehouse
from bom_guardian.warehouse.local import LocalWarehouse


def get_warehouse_backend(settings=None) -> Warehouse:  # type: ignore[no-untyped-def]
    """Return the configured warehouse backend.

    DuckDB by default; Snowflake when BOMG_WAREHOUSE_BACKEND=snowflake (requires the
    `snowflake` extra and SNOWFLAKE_* env vars — external execution pending).
    """
    from bom_guardian.config import WarehouseBackend, get_settings

    settings = settings or get_settings()
    if settings.warehouse_backend is WarehouseBackend.SNOWFLAKE:
        from bom_guardian.warehouse.snowflake import SnowflakeWarehouse

        return SnowflakeWarehouse(settings)
    return LocalWarehouse(settings.duckdb_path)


__all__ = ["SCHEMAS", "LocalWarehouse", "Warehouse", "get_warehouse_backend"]
