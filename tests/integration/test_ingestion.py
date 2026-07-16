"""Integration tests: generator output -> raw layer with audit + idempotency."""

from pathlib import Path

import pandas as pd
import pytest
from data_generator.config.profiles import PROFILES, ProfileConfig
from data_generator.orchestrator import run_generation

from bom_guardian.ingestion import IngestionService
from bom_guardian.warehouse import LocalWarehouse

TINY = ProfileConfig(name="tiny", n_parts=150, n_suppliers=15, n_plants=2, warehouses_per_plant=1)


@pytest.fixture(scope="module")
def output_dir(tmp_path_factory) -> Path:  # type: ignore[no-untyped-def]
    PROFILES["tiny"] = TINY
    root = tmp_path_factory.mktemp("gen")
    run_generation("tiny", seed=5, output_root=root, inject=True)
    return root / "tiny"


@pytest.fixture()
def service():  # type: ignore[no-untyped-def]
    with LocalWarehouse(":memory:") as wh:
        yield IngestionService(wh)


@pytest.mark.integration
def test_full_directory_ingest_with_audit(service, output_dir) -> None:  # type: ignore[no-untyped-def]
    result = service.ingest_directory(output_dir, profile="tiny")
    assert result["loaded_files"] == 22
    assert result["rows_loaded"] > 0
    batches = service.wh.query("SELECT * FROM ops.load_batches")
    assert len(batches) == 1
    assert batches.iloc[0]["status"] == "COMPLETED"
    files = service.wh.query("SELECT * FROM ops.load_files")
    assert len(files) == 22


@pytest.mark.integration
def test_audit_columns_present(service, output_dir) -> None:  # type: ignore[no-untyped-def]
    service.ingest_directory(output_dir, profile="tiny")
    parts = service.wh.query("SELECT * FROM raw.part_master LIMIT 5")
    for col in [
        "_ingestion_batch_id",
        "_ingested_at",
        "_file_hash",
        "_row_hash",
        "_schema_version",
        "_record_seq",
        "_load_status",
    ]:
        assert col in parts.columns
    assert parts["_row_hash"].nunique() == len(parts)


@pytest.mark.integration
def test_reingest_is_idempotent(service, output_dir) -> None:  # type: ignore[no-untyped-def]
    first = service.ingest_directory(output_dir, profile="tiny")
    count_after_first = service.wh.count("raw", "part_master")
    second = service.ingest_directory(output_dir, profile="tiny")
    assert second["loaded_files"] == 0
    assert second["skipped_files"] == 22
    assert service.wh.count("raw", "part_master") == count_after_first
    assert first["rows_loaded"] > 0


@pytest.mark.integration
def test_null_pk_rows_rejected(service, tmp_path) -> None:  # type: ignore[no-untyped-def]
    bad = pd.DataFrame({"part_id": ["P1", None, "P3"], "description": ["a", "b", "c"]})
    path = tmp_path / "part_master.csv"
    bad.to_csv(path, index=False)
    result = service.ingest_file(path, "BATCH-TEST", "tiny")
    assert result["loaded"] == 2
    assert result["rejected"] == 1
    rejected = service.wh.query("SELECT * FROM ops.rejected_records")
    assert len(rejected) == 1
    assert "null primary key" in rejected.iloc[0]["reason"]


@pytest.mark.integration
def test_ground_truth_loads_to_isolated_schema(service, output_dir) -> None:  # type: ignore[no-untyped-def]
    n = service.load_ground_truth(output_dir / "ground_truth" / "labels.csv")
    assert n > 0
    assert "labels" in service.wh.tables("ground_truth")
    # raw layer must not contain ground truth
    assert "labels" not in service.wh.tables("raw")
