"""Clean-baseline + detection tests (hardening H3).

Proves (a) the generator produces a clean baseline — no non-allowlisted rule fires
before injection — and (b) baseline-diff detection recovers injected defects. These
lock in the properties the H3 evaluation depends on so they cannot silently regress.
"""

from pathlib import Path

import pytest
from data_generator.config.profiles import PROFILES, ProfileConfig
from data_generator.orchestrator import run_generation

from bom_guardian.ingestion import IngestionService
from bom_guardian.quality import RuleEngine
from bom_guardian.testing import TRANSFORM_SQL
from bom_guardian.warehouse import LocalWarehouse

# Rules allowed to fire organically (intentional statistical realism). Mirrors
# scripts/validate_clean_baseline.py BASELINE_ALLOWLIST.
ALLOWLIST = {
    "COMP-008",
    "XFLD-001",
    "TEMP-002",
    "ANOM-001",
    "ANOM-002",
    "ANOM-004",
    "DOCR-001",
    "DOCR-002",
    "DOCR-003",
    "GRPH-003",
}


def _warehouse(tmp_path: Path, *, inject: bool) -> LocalWarehouse:
    PROFILES["cbtiny"] = ProfileConfig(
        name="cbtiny", n_parts=400, n_suppliers=40, n_plants=2, warehouses_per_plant=1
    )
    run_generation("cbtiny", seed=17, output_root=tmp_path, inject=inject, inject_rate=0.04)
    wh = LocalWarehouse(":memory:")
    svc = IngestionService(wh)
    svc.ingest_directory(tmp_path / "cbtiny", profile="cbtiny")
    if inject:
        svc.load_ground_truth(tmp_path / "cbtiny" / "ground_truth" / "labels.csv")
    for sql in TRANSFORM_SQL:
        wh.execute(sql)
    RuleEngine(wh).run_all()
    return wh


@pytest.mark.data_quality
def test_clean_baseline_only_allowlisted_rules_fire(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with _warehouse(tmp_path, inject=False) as wh:
        fired = wh.query("SELECT DISTINCT rule_id FROM quality.dq_issues")
        rule_ids = set(fired["rule_id"])
    unexpected = rule_ids - ALLOWLIST
    assert not unexpected, f"clean baseline is not clean; non-allowlisted rules fired: {unexpected}"


@pytest.mark.data_quality
def test_injection_creates_new_detections_by_baseline_diff(tmp_path) -> None:  # type: ignore[no-untyped-def]
    # structural defects that must NOT exist on the clean baseline and MUST appear
    # only after injection (pure baseline-diff signal)
    structural_rules = ["REFI-001", "REFI-002", "GRPH-001", "VALD-006", "VALD-007"]
    with _warehouse(tmp_path / "clean", inject=False) as clean:
        for rid in structural_rules:
            n = clean.query(
                f"SELECT COUNT(*) AS n FROM quality.dq_issues WHERE rule_id = '{rid}'"
            ).iloc[0]["n"]
            assert n == 0, f"{rid} fired on the clean baseline ({n}) — baseline not clean"
    with _warehouse(tmp_path / "inj", inject=True) as inj:
        total = inj.query(
            "SELECT COUNT(*) AS n FROM quality.dq_issues WHERE rule_id IN "
            f"({', '.join(repr(r) for r in structural_rules)})"
        ).iloc[0]["n"]
        assert total > 0, "injection produced no structural defects"
