"""TRUE end-to-end test that invokes the REAL dbt project (hardening H4).

Unlike test_full_platform.py (which uses hand-written TRANSFORM_SQL views), this test
runs the actual dbt project against a persistent DuckDB file and fails if any real dbt
model, source, relationship, or mart breaks. It then runs the full engine + API loop
against the dbt-built warehouse.

It is slower (spawns `dbt build` twice) and marked `e2e`. dbt-duckdb must be installed
(`pip install -e ".[dbt]"`); the test skips cleanly if it is not.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
from api.app.dependencies import get_remediation_engine, get_warehouse
from api.app.main import app
from data_generator.config.profiles import PROFILES, ProfileConfig
from data_generator.orchestrator import run_generation
from fastapi.testclient import TestClient

from bom_guardian.ai import DeterministicMockAIProvider, RemediationEngine
from bom_guardian.ingestion import IngestionService
from bom_guardian.quality import QualityScorer, RuleEngine
from bom_guardian.warehouse import LocalWarehouse

REPO = Path(__file__).resolve().parents[2]
DBT_DIR = REPO / "dbt_supply_chain"

CORE_MODELS = [
    "dim_part",
    "dim_supplier",
    "dim_plant",
    "dim_warehouse",
    "dim_date",
    "fact_bom_relationship",
    "fact_inventory",
    "fact_future_demand",
    "fact_purchase_order",
    "fact_standard_cost",
    "fact_lead_time",
]
MARTS = [
    "mart_executive_quality",
    "mart_part_quality",
    "mart_bom_integrity",
    "mart_supplier_quality",
    "mart_business_impact",
    "mart_remediation_performance",
    "mart_ai_governance",
]


def _dbt_available() -> bool:
    try:
        import dbt.cli.main  # noqa: F401

        return True
    except Exception:
        return False


def _run_dbt(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "dbt.cli.main", *args, "--profiles-dir", ".", "--project-dir", "."],
        cwd=DBT_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.mark.e2e
@pytest.mark.skipif(not _dbt_available(), reason="dbt-duckdb not installed")
def test_real_dbt_pipeline_end_to_end(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db = tmp_path / "e2e_dbt.duckdb"
    env = {**os.environ, "BOMG_DUCKDB_PATH": str(db)}

    # 1-2. generate + inject a small profile (still exercises every dbt model)
    PROFILES["e2edbt"] = ProfileConfig(
        name="e2edbt", n_parts=250, n_suppliers=25, n_plants=2, warehouses_per_plant=1
    )
    gen = tmp_path / "gen"
    run_generation("e2edbt", seed=11, output_root=gen, inject=True, inject_rate=0.04)

    # 3. load the actual persistent DuckDB warehouse
    with LocalWarehouse(db) as wh:
        svc = IngestionService(wh)
        svc.ingest_directory(gen / "e2edbt", profile="e2edbt")
        svc.load_ground_truth(gen / "e2edbt" / "ground_truth" / "labels.csv")

    # 4. invoke the REAL dbt project for staging + core
    result = _run_dbt(["build", "--exclude", "marts"], env)
    assert result.returncode == 0, (
        f"dbt staging/core build failed:\n{result.stdout}\n{result.stderr}"
    )

    # 5-6. verify staging views and core models exist with rows
    with LocalWarehouse(db) as wh:
        assert wh.count("staging", "stg_part_master") > 0
        for model in CORE_MODELS:
            assert wh.count("core", model) > 0, f"core.{model} empty after dbt build"

        # drift guard: the dbt-built dim_part must expose the same columns the fast
        # TRANSFORM_SQL fixture produces, so the test fixture cannot silently diverge.
        _assert_no_fixture_drift(wh, gen)

        # 7-8. quality rules, scoring, impact inputs
        summary = RuleEngine(wh).run_all()
        assert summary["rules_failed"] == 0 and summary["issues_created"] > 0
        QualityScorer(wh).run_all()
        RemediationEngine(DeterministicMockAIProvider(), warehouse=wh)  # creates audit table
        from api.app.services import IssueService

        IssueService(wh)  # creates decisions table
        baseline_parts = wh.query("SELECT * FROM core.dim_part ORDER BY part_key")

    # dbt builds the 7 marts from the quality tables just created
    result = _run_dbt(["build", "--select", "marts"], env)
    assert result.returncode == 0, f"dbt marts build failed:\n{result.stdout}\n{result.stderr}"
    with LocalWarehouse(db) as wh:
        for mart in MARTS:
            wh.query(f"SELECT * FROM marts.{mart} LIMIT 1")  # raises if the mart is missing

    # 9-16. full API loop against the dbt-built warehouse
    api_wh = LocalWarehouse(db)
    app.dependency_overrides[get_warehouse] = lambda: api_wh
    app.dependency_overrides[get_remediation_engine] = lambda: RemediationEngine(
        DeterministicMockAIProvider(), warehouse=api_wh
    )
    try:
        with TestClient(app, headers={"Authorization": "Bearer demo-steward-token"}) as client:
            assert client.get("/api/v1/readiness").status_code == 200
            issue_id = api_wh.query(
                "SELECT issue_id FROM quality.dq_issues WHERE status = 'DETECTED' LIMIT 1"
            ).iloc[0]["issue_id"]

            rec = client.post(f"/api/v1/issues/{issue_id}/recommendations")
            assert rec.status_code == 200 and rec.json()["human_review_required"] is True

            approved = client.post(
                f"/api/v1/issues/{issue_id}/approve",
                json={"reason": "verified through real dbt pipeline"},
            )
            assert approved.status_code == 200 and approved.json()["status"] == "APPROVED"

            # 15. baseline (core master data) unchanged by the workflow
            after = api_wh.query("SELECT * FROM core.dim_part ORDER BY part_key")
            pd.testing.assert_frame_equal(baseline_parts, after)

            # 16. audit history
            history = client.get(f"/api/v1/issues/{issue_id}/history").json()
            assert len(history) == 1 and history[0]["reviewer"] == "demo.steward"
    finally:
        app.dependency_overrides.clear()
        api_wh.close()


def _assert_no_fixture_drift(dbt_wh: LocalWarehouse, gen: Path) -> None:
    """core.dim_part built by dbt must have the same columns as the TRANSFORM_SQL fixture."""
    from bom_guardian.testing import TRANSFORM_SQL

    dbt_cols = set(dbt_wh.query("SELECT * FROM core.dim_part LIMIT 0").columns)
    with LocalWarehouse(":memory:") as fx:
        svc = IngestionService(fx)
        svc.ingest_directory(gen / "e2edbt", profile="e2edbt")
        for sql in TRANSFORM_SQL:
            fx.execute(sql)
        fixture_cols = set(fx.query("SELECT * FROM core.dim_part LIMIT 0").columns)
    missing = fixture_cols - dbt_cols
    assert not missing, (
        f"TRANSFORM_SQL fixture has drifted from the dbt model; columns not in dbt "
        f"dim_part: {missing}. Update src/bom_guardian/testing.py to match the dbt model."
    )
