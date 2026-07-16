"""Tests for the DuckDB local warehouse."""

import pandas as pd
import pytest

from bom_guardian.warehouse import SCHEMAS, LocalWarehouse


@pytest.fixture()
def wh():  # type: ignore[no-untyped-def]
    with LocalWarehouse(":memory:") as w:
        yield w


def test_all_layer_schemas_created(wh: LocalWarehouse) -> None:
    layout = wh.validate()
    assert set(layout.keys()) == set(SCHEMAS)


def test_load_and_query_roundtrip(wh: LocalWarehouse) -> None:
    df = pd.DataFrame({"part_id": ["P1", "P2"], "cost": [1.5, 2.5]})
    n = wh.load_dataframe("raw", "part_master", df)
    assert n == 2
    out = wh.query("SELECT * FROM raw.part_master ORDER BY part_id")
    assert out["part_id"].tolist() == ["P1", "P2"]


def test_append_mode(wh: LocalWarehouse) -> None:
    df = pd.DataFrame({"x": [1]})
    wh.load_dataframe("ops", "t", df)
    wh.load_dataframe("ops", "t", df, replace=False)
    assert wh.count("ops", "t") == 2


def test_unknown_schema_rejected(wh: LocalWarehouse) -> None:
    with pytest.raises(ValueError):
        wh.load_dataframe("nope", "t", pd.DataFrame({"x": [1]}))


def test_persistent_file(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "wh.duckdb"
    with LocalWarehouse(path) as w:
        w.load_dataframe("raw", "t", pd.DataFrame({"x": [1, 2, 3]}))
    with LocalWarehouse(path) as w2:
        assert w2.count("raw", "t") == 3
