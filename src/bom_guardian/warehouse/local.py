"""DuckDB local warehouse — schema-parallel to the Snowflake target.

The same logical layers exist in both backends (RAW/STAGING/CORE/QUALITY/MARTS/
GROUND_TRUTH/OPS) so SQL written against layer-qualified names is portable.
"""

from __future__ import annotations

import threading
from pathlib import Path
from types import TracebackType

import duckdb
import pandas as pd

from bom_guardian.observability import get_logger

SCHEMAS: list[str] = [
    "raw",
    "staging",
    "core",
    "quality",
    "marts",
    "ground_truth",
    "ops",
]


class LocalWarehouse:
    """Thin wrapper around a DuckDB database with the platform's schema layout."""

    def __init__(self, db_path: Path | str = ":memory:") -> None:
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._path = str(db_path)
        self.conn = duckdb.connect(self._path)
        # DuckDB connections are not safe for concurrent cursor use; the API
        # serves requests from a threadpool, so serialize access.
        self._lock = threading.Lock()
        self._log = get_logger("local_warehouse", db=self._path)
        self._ensure_schemas()

    def _ensure_schemas(self) -> None:
        for schema in SCHEMAS:
            self.conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    # -- API ------------------------------------------------------------------
    def load_dataframe(
        self, schema: str, table: str, df: pd.DataFrame, replace: bool = True
    ) -> int:
        """Load a DataFrame into schema.table. Returns row count."""
        if schema not in SCHEMAS:
            raise ValueError(f"Unknown schema '{schema}'; expected one of {SCHEMAS}")
        with self._lock:
            self.conn.register("_incoming", df)
            mode = "CREATE OR REPLACE TABLE" if replace else "INSERT INTO"
            if replace:
                self.conn.execute(f"{mode} {schema}.{table} AS SELECT * FROM _incoming")
            else:
                self.conn.execute(f"INSERT INTO {schema}.{table} SELECT * FROM _incoming")
            self.conn.unregister("_incoming")
        n = self.count(schema, table)
        self._log.info("table_loaded", schema=schema, table=table, rows=len(df))
        return n

    def query(self, sql: str) -> pd.DataFrame:
        with self._lock:
            return self.conn.execute(sql).df()

    def execute(self, sql: str) -> None:
        with self._lock:
            self.conn.execute(sql)

    def count(self, schema: str, table: str) -> int:
        with self._lock:
            row = self.conn.execute(f"SELECT COUNT(*) FROM {schema}.{table}").fetchone()
        return int(row[0]) if row else 0

    def tables(self, schema: str) -> list[str]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = ?",
                [schema],
            ).fetchall()
        return sorted(r[0] for r in rows)

    def validate(self) -> dict[str, list[str]]:
        """Return schema -> tables mapping; raises if a layer schema is missing."""
        with self._lock:
            existing = {
                r[0]
                for r in self.conn.execute(
                    "SELECT schema_name FROM information_schema.schemata"
                ).fetchall()
            }
        missing = [s for s in SCHEMAS if s not in existing]
        if missing:
            raise RuntimeError(f"Warehouse missing schemas: {missing}")
        return {s: self.tables(s) for s in SCHEMAS}

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> LocalWarehouse:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
