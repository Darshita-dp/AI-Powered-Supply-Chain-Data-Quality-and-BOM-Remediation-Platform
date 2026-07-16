"""Warehouse backends: DuckDB local fallback (default) and Snowflake target."""

from bom_guardian.warehouse.local import SCHEMAS, LocalWarehouse

__all__ = ["SCHEMAS", "LocalWarehouse"]
