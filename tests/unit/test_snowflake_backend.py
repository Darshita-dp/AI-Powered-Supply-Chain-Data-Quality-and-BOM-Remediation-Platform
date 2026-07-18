"""Fake-connection tests for the Snowflake adapter and modernized AI provider.

These exercise the SQL/logic without a live Snowflake account (none is configured).
They are explicitly NOT a substitute for real Snowflake validation — see
docs/limitations.md. A live run would use tests marked to skip without credentials.
"""

from __future__ import annotations

import json

import pytest

from bom_guardian.ai import EvidenceBundle, SnowflakeCortexAIProvider
from bom_guardian.ai.schemas import EvidenceItem
from bom_guardian.warehouse.base import SCHEMAS, Warehouse
from bom_guardian.warehouse.snowflake import SnowflakeWarehouse


class FakeCursor:
    def __init__(self, conn: FakeConnection) -> None:
        self._conn = conn
        self.description: list[tuple] | None = None
        self._rows: list[tuple] = []

    def execute(self, sql: str, params=None):  # type: ignore[no-untyped-def]
        self._conn.executed.append((sql, params))
        if self._conn.raise_on_execute:
            raise RuntimeError("boom")
        rows, cols = self._conn.resolve(sql)
        self._rows = rows
        self.description = [(c,) for c in cols] if cols else None
        return self

    def fetchall(self):  # type: ignore[no-untyped-def]
        return self._rows

    def fetchone(self):  # type: ignore[no-untyped-def]
        return self._rows[0] if self._rows else None

    def close(self) -> None:
        pass


class FakeConnection:
    """Programmable fake: maps an SQL substring to (rows, columns)."""

    def __init__(self, responses: dict[str, tuple[list[tuple], list[str]]] | None = None) -> None:
        self.responses = responses or {}
        self.executed: list[tuple] = []
        self.raise_on_execute = False

    def resolve(self, sql: str) -> tuple[list[tuple], list[str]]:
        for needle, resp in self.responses.items():
            if needle in sql:
                return resp
        return [], []

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def close(self) -> None:
        pass


# --------------------------------------------------------------------------
# Warehouse adapter
# --------------------------------------------------------------------------


def test_snowflake_warehouse_conforms_to_protocol() -> None:
    wh = SnowflakeWarehouse(connection=FakeConnection())
    assert isinstance(wh, Warehouse)


def test_tables_and_table_exists_use_information_schema() -> None:
    conn = FakeConnection(
        {"information_schema.tables": ([("DIM_PART",), ("DQ_ISSUES",)], ["TABLE_NAME"])}
    )
    wh = SnowflakeWarehouse(connection=conn)
    assert wh.tables("core") == ["dim_part", "dq_issues"]
    assert wh.table_exists("core", "dim_part")
    assert not wh.table_exists("core", "missing")
    # parameterized: schema name is bound, not interpolated
    assert any(p == ["CORE"] for _, p in conn.executed)


def test_validate_requires_all_layer_schemas() -> None:
    all_schemas = ([(s.upper(),) for s in SCHEMAS], ["SCHEMA_NAME"])
    wh = SnowflakeWarehouse(
        connection=FakeConnection(
            {
                "information_schema.schemata": all_schemas,
                "information_schema.tables": ([], ["TABLE_NAME"]),
            }
        )
    )
    layout = wh.validate()
    assert set(layout) == set(SCHEMAS)


def test_validate_raises_on_missing_schema() -> None:
    partial = ([("raw".upper(),)], ["SCHEMA_NAME"])
    wh = SnowflakeWarehouse(connection=FakeConnection({"information_schema.schemata": partial}))
    with pytest.raises(RuntimeError, match="missing schemas"):
        wh.validate()


def test_count_reads_scalar() -> None:
    wh = SnowflakeWarehouse(connection=FakeConnection({"COUNT(*)": ([(42,)], ["N"])}))
    assert wh.count("core", "dim_part") == 42


def test_load_dataframe_rejects_unknown_schema() -> None:
    import pandas as pd

    wh = SnowflakeWarehouse(connection=FakeConnection())
    with pytest.raises(ValueError, match="Unknown schema"):
        wh.load_dataframe("nope", "t", pd.DataFrame({"x": [1]}))


# --------------------------------------------------------------------------
# Modernized AI provider
# --------------------------------------------------------------------------


def _bundle() -> EvidenceBundle:
    return EvidenceBundle(
        issue_id="ISS-1",
        issue_summary="duplicate part records",
        items=[
            EvidenceItem(evidence_id=f"EVD-{i}", kind="rule_violation", summary=f"e{i}")
            for i in range(1, 3)
        ],
    )


def _proposal_json() -> str:
    return json.dumps(
        {
            "issue_id": "ISS-1",
            "recommended_action": "merge_records",
            "evidence_refs": ["EVD-1", "EVD-2"],
            "confidence": 0.8,
            "human_review_required": True,
            "explanation": "grounded in [EVD-1]",
        }
    )


def test_provider_uses_ai_complete_not_legacy_cortex() -> None:
    conn = FakeConnection({"AI_COMPLETE": ([(_proposal_json(),)], ["X"])})
    provider = SnowflakeCortexAIProvider(connection=conn, model="claude-3-5-sonnet")
    out = provider.propose("system", _bundle())
    assert out["recommended_action"] == "merge_records"
    assert out["provider"] == "snowflake_cortex"
    assert out["model"] == "claude-3-5-sonnet"
    executed_sql = " ".join(sql for sql, _ in conn.executed)
    assert "AI_COMPLETE" in executed_sql
    assert "CORTEX.COMPLETE" not in executed_sql  # legacy function must not be used
    assert provider.last_usage["latency_ms"] >= 0


def test_provider_requires_connection() -> None:
    with pytest.raises(RuntimeError, match=r"external.*execution pending"):
        SnowflakeCortexAIProvider(connection=None).propose("s", _bundle())


def test_provider_surfaces_call_errors() -> None:
    conn = FakeConnection()
    conn.raise_on_execute = True
    with pytest.raises(RuntimeError, match="AI_COMPLETE call failed"):
        SnowflakeCortexAIProvider(connection=conn).propose("s", _bundle())


def test_provider_rejects_non_json() -> None:
    conn = FakeConnection({"AI_COMPLETE": ([("not json",)], ["X"])})
    with pytest.raises(ValueError, match="non-JSON"):
        SnowflakeCortexAIProvider(connection=conn).propose("s", _bundle())


def test_provider_rejects_empty_content() -> None:
    conn = FakeConnection({"AI_COMPLETE": ([(None,)], ["X"])})
    with pytest.raises(ValueError, match="no content"):
        SnowflakeCortexAIProvider(connection=conn).propose("s", _bundle())


def test_provider_unwraps_structured_output() -> None:
    wrapped = json.dumps({"structured_output": json.loads(_proposal_json())})
    conn = FakeConnection({"AI_COMPLETE": ([(wrapped,)], ["X"])})
    out = SnowflakeCortexAIProvider(connection=conn).propose("s", _bundle())
    assert out["issue_id"] == "ISS-1"
