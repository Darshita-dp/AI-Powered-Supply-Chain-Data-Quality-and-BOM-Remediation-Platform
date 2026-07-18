"""Warehouse abstraction shared by the DuckDB and Snowflake backends.

Both backends expose the same logical layers (schemas) and the same small API, so
engine/API/pipeline code is backend-agnostic. `Warehouse` is a structural Protocol —
`LocalWarehouse` and `SnowflakeWarehouse` conform to it without inheriting from it.
"""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, runtime_checkable

import pandas as pd

SCHEMAS: list[str] = [
    "raw",
    "staging",
    "core",
    "quality",
    "marts",
    "ground_truth",
    "ops",
]


@runtime_checkable
class Warehouse(Protocol):
    """The backend-agnostic warehouse contract used across the platform."""

    def load_dataframe(
        self, schema: str, table: str, df: pd.DataFrame, replace: bool = True
    ) -> int: ...

    def query(self, sql: str, params: list | tuple | None = None) -> pd.DataFrame: ...

    def execute(self, sql: str, params: list | tuple | None = None) -> None: ...

    def count(self, schema: str, table: str) -> int: ...

    def tables(self, schema: str) -> list[str]: ...

    def table_exists(self, schema: str, table: str) -> bool: ...

    def validate(self) -> dict[str, list[str]]: ...

    def close(self) -> None: ...

    def __enter__(self) -> Warehouse: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
