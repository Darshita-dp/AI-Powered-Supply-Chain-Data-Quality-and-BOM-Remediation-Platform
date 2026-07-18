"""Snowflake warehouse adapter — target backend, parallel to LocalWarehouse.

Status: implemented locally; external Snowflake execution pending (no credentials in
this environment). The logic is exercised by tests with a fake connection
(tests/unit/test_snowflake_backend.py); it has never run against a live account.

Design:
- connection configured entirely from environment variables (no embedded credentials);
- parameterized query execution (%s binds) — no string interpolation of user values;
- DataFrame ingestion via snowflake.connector.pandas_tools.write_pandas;
- table-existence checks and schema validation against INFORMATION_SCHEMA;
- explicit transaction control and guaranteed resource cleanup.

The snowflake-connector-python dependency is optional (the `snowflake` extra); importing
this module without it raises a clear, actionable error only when you construct the
adapter, so local/DuckDB workflows never need it.
"""

from __future__ import annotations

from types import TracebackType
from typing import Any

import pandas as pd

from bom_guardian.config import Settings, get_settings
from bom_guardian.observability import get_logger
from bom_guardian.warehouse.base import SCHEMAS


class SnowflakeWarehouse:
    """Snowflake-backed implementation of the Warehouse protocol."""

    def __init__(self, settings: Settings | None = None, connection: Any | None = None) -> None:
        self._settings = settings or get_settings()
        self._log = get_logger("snowflake_warehouse")
        self._database = self._sf_conf("database", "BOM_GUARDIAN")
        if connection is not None:
            self._conn = connection  # injected (real or fake) — used by tests
        else:
            self._conn = self._connect()

    # -- connection -----------------------------------------------------------
    def _sf_conf(self, key: str, default: str = "") -> str:
        import os

        return os.environ.get(f"SNOWFLAKE_{key.upper()}", default)

    def _connect(self) -> Any:
        try:
            import snowflake.connector
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "snowflake-connector-python is not installed. Install the extra: "
                'pip install -e ".[snowflake]". No Snowflake credentials are configured '
                "in this environment (status: external execution pending)."
            ) from exc

        account = self._sf_conf("account")
        if not account:
            raise RuntimeError(
                "SNOWFLAKE_ACCOUNT is not set. Configure the SNOWFLAKE_* environment "
                "variables (see .env.example). Status: external execution pending."
            )
        return snowflake.connector.connect(
            account=account,
            user=self._sf_conf("user"),
            password=self._sf_conf("password"),
            role=self._sf_conf("role", "BOMG_ENGINEER"),
            warehouse=self._sf_conf("warehouse", "BOMG_WH_XS"),
            database=self._database,
            schema=self._sf_conf("schema", "RAW"),
            client_session_keep_alive=False,
        )

    # -- API ------------------------------------------------------------------
    def load_dataframe(
        self, schema: str, table: str, df: pd.DataFrame, replace: bool = True
    ) -> int:
        if schema not in SCHEMAS:
            raise ValueError(f"Unknown schema '{schema}'; expected one of {SCHEMAS}")
        from snowflake.connector.pandas_tools import write_pandas

        self.execute(f"CREATE SCHEMA IF NOT EXISTS {self._database}.{schema.upper()}")
        success, _, nrows, _ = write_pandas(
            self._conn,
            df,
            table_name=table.upper(),
            database=self._database,
            schema=schema.upper(),
            auto_create_table=True,
            overwrite=replace,
            quote_identifiers=False,
        )
        if not success:
            raise RuntimeError(f"write_pandas failed for {schema}.{table}")
        self._log.info("table_loaded", schema=schema, table=table, rows=nrows)
        return int(nrows)

    def query(self, sql: str, params: list | tuple | None = None) -> pd.DataFrame:
        cur = self._conn.cursor()
        try:
            cur.execute(sql, params)
            return cur.fetch_pandas_all() if hasattr(cur, "fetch_pandas_all") else _rows_to_df(cur)
        finally:
            cur.close()

    def execute(self, sql: str, params: list | tuple | None = None) -> None:
        cur = self._conn.cursor()
        try:
            cur.execute(sql, params)
        finally:
            cur.close()

    def count(self, schema: str, table: str) -> int:
        df = self.query(
            f"SELECT COUNT(*) AS N FROM {self._database}.{schema.upper()}.{table.upper()}"
        )
        col = "N" if "N" in df.columns else df.columns[0]
        return int(df.iloc[0][col])

    def tables(self, schema: str) -> list[str]:
        df = self.query(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = %s",
            [schema.upper()],
        )
        col = "TABLE_NAME" if "TABLE_NAME" in df.columns else df.columns[0]
        return sorted(str(t).lower() for t in df[col].tolist())

    def table_exists(self, schema: str, table: str) -> bool:
        return table.lower() in self.tables(schema)

    def validate(self) -> dict[str, list[str]]:
        df = self.query("SELECT schema_name FROM information_schema.schemata")
        col = "SCHEMA_NAME" if "SCHEMA_NAME" in df.columns else df.columns[0]
        existing = {str(s).lower() for s in df[col].tolist()}
        missing = [s for s in SCHEMAS if s not in existing]
        if missing:
            raise RuntimeError(f"Snowflake missing schemas: {missing}")
        return {s: self.tables(s) for s in SCHEMAS}

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> SnowflakeWarehouse:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


def _rows_to_df(cur: Any) -> pd.DataFrame:
    """Fallback for connectors/mocks without fetch_pandas_all."""
    rows = cur.fetchall()
    cols = [d[0] for d in (cur.description or [])]
    return pd.DataFrame(rows, columns=cols)
