"""End-to-end platform test: the full loop from generation to audited approval.

Steps (per the build specification):
 1. generate smoke-scale data       7. create issues
 2. inject known defects            8. calculate impact
 3. load local storage              9. generate a mock recommendation
 4. run transformations            10. retrieve the issue through the API
 5. run quality rules              11. simulate reviewer approval (no baseline mutation)
 6. run entity resolution          12. verify audit history
"""

import pandas as pd
import pytest
from api.app.dependencies import get_remediation_engine, get_warehouse
from api.app.main import app
from fastapi.testclient import TestClient

from bom_guardian.ai import DeterministicMockAIProvider, RemediationEngine
from bom_guardian.bom_graph import BomGraph
from bom_guardian.entity_resolution import WeightedMatcher
from bom_guardian.impact_twin import ImpactTwin
from bom_guardian.quality import RuleEngine
from bom_guardian.testing import build_test_warehouse


@pytest.mark.e2e
def test_full_platform_loop(tmp_path_factory) -> None:  # type: ignore[no-untyped-def]
    # 1-4: generate, inject, ingest, transform
    wh = build_test_warehouse(tmp_path_factory.mktemp("e2e"), n_parts=300, seed=11)
    try:
        # 5: quality rules
        summary = RuleEngine(wh).run_all()
        assert summary["rules_failed"] == 0
        assert summary["issues_created"] > 0

        # 6: entity resolution finds injected duplicates
        parts = wh.query(
            "SELECT part_key AS part_id, source_part_number, source_system, description, "
            "category, uom, manufacturer_part_number, standard_cost, lead_time_days, "
            "primary_plant, lifecycle_status FROM core.dim_part"
        )
        matches = WeightedMatcher().find_matches(parts)
        assert matches, "expected duplicate candidates from injected data"

        # 7: issues exist with evidence
        issue = wh.query(
            "SELECT issue_id, entity_key FROM quality.dq_issues "
            "WHERE entity_type = 'part' AND status = 'DETECTED' LIMIT 1"
        ).iloc[0]

        # 8: impact for the affected part
        comps = wh.query(
            "SELECT parent_part_key AS parent_part_id, child_part_key AS child_part_id, "
            "quantity_per, bom_rel_key AS bom_component_id FROM core.fact_bom_relationship"
        )
        twin = ImpactTwin(
            graph=BomGraph.from_components(comps),
            parts=parts.rename(columns={"part_id": "part_id"}),
            inventory=wh.query(
                "SELECT part_key AS part_id, on_hand_value FROM core.fact_inventory"
            ),
            future_demand=wh.query(
                "SELECT part_key AS part_id, demand_qty FROM core.fact_future_demand"
            ),
            po_lines=wh.query(
                "SELECT part_key AS part_id, line_value FROM core.fact_purchase_order"
            ),
            production_orders=wh.query("SELECT part_id, status FROM raw.production_orders"),
            supplier_parts=wh.query("SELECT part_id, supplier_id FROM raw.supplier_parts"),
        )
        impact = twin.blast_radius(str(issue["entity_key"]))
        assert impact["operational_priority"] >= 0

        # 9-12 through the API
        app.dependency_overrides[get_warehouse] = lambda: wh
        app.dependency_overrides[get_remediation_engine] = lambda: RemediationEngine(
            DeterministicMockAIProvider(), warehouse=wh
        )
        baseline_parts = wh.query("SELECT * FROM core.dim_part ORDER BY part_key")
        with TestClient(app) as client:
            # 9: mock recommendation
            rec = client.post(f"/api/v1/issues/{issue['issue_id']}/recommendations")
            assert rec.status_code == 200
            assert rec.json()["human_review_required"] is True

            # 10: retrieve issue through the API
            got = client.get(f"/api/v1/issues/{issue['issue_id']}")
            assert got.status_code == 200
            assert got.json()["issue_id"] == issue["issue_id"]

            # 11: reviewer approval
            approved = client.post(
                f"/api/v1/issues/{issue['issue_id']}/approve",
                json={"reviewer": "e2e-reviewer", "reason": "verified end to end"},
            )
            assert approved.status_code == 200
            assert approved.json()["status"] == "APPROVED"

            # baseline (core/master data) must be unchanged by the whole workflow
            after_parts = wh.query("SELECT * FROM core.dim_part ORDER BY part_key")
            pd.testing.assert_frame_equal(baseline_parts, after_parts)

            # 12: audit history
            history = client.get(f"/api/v1/issues/{issue['issue_id']}/history").json()
            assert len(history) == 1
            assert history[0]["reviewer"] == "e2e-reviewer"
            assert history[0]["before_status"] == "DETECTED"
            assert history[0]["after_status"] == "APPROVED"

            # AI call was audited
            gov = client.get("/api/v1/analytics/ai-governance").json()
            assert gov["calls"] >= 1
    finally:
        app.dependency_overrides.clear()
        wh.close()
