"""API tests against a fully-populated in-memory warehouse (no mock data)."""

import pytest
from fastapi.testclient import TestClient

from api.app.dependencies import get_remediation_engine, get_warehouse
from api.app.main import app
from bom_guardian.ai import DeterministicMockAIProvider, RemediationEngine
from bom_guardian.quality import RuleEngine
from bom_guardian.testing import build_test_warehouse


@pytest.fixture(scope="module")
def client(tmp_path_factory):  # type: ignore[no-untyped-def]
    wh = build_test_warehouse(tmp_path_factory.mktemp("api"), n_parts=300, seed=11)
    RuleEngine(wh).run_all()
    app.dependency_overrides[get_warehouse] = lambda: wh
    app.dependency_overrides[get_remediation_engine] = lambda: RemediationEngine(
        DeterministicMockAIProvider(), warehouse=wh
    )
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()
    wh.close()


def _first_issue(client, **params):  # type: ignore[no-untyped-def]
    r = client.get("/api/v1/issues", params={"page_size": 1, **params})
    assert r.status_code == 200
    return r.json()["items"][0]


def test_health_and_readiness(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/api/v1/health").json()["status"] == "ok"
    ready = client.get("/api/v1/readiness")
    assert ready.status_code == 200
    assert ready.json()["schemas"]["quality"] > 0


def test_correlation_id_header(client) -> None:  # type: ignore[no-untyped-def]
    r = client.get("/api/v1/health")
    assert r.headers["X-Correlation-ID"].startswith("REQ-")
    r2 = client.get("/api/v1/health", headers={"X-Correlation-ID": "REQ-fixed"})
    assert r2.headers["X-Correlation-ID"] == "REQ-fixed"


def test_parts_pagination_filtering_sorting(client) -> None:  # type: ignore[no-untyped-def]
    r = client.get(
        "/api/v1/parts",
        params={"page": 1, "page_size": 5, "sort_by": "standard_cost", "sort_dir": "desc"},
    )
    body = r.json()
    assert r.status_code == 200
    assert len(body["items"]) == 5
    costs = [i["standard_cost"] for i in body["items"] if i["standard_cost"] is not None]
    assert costs == sorted(costs, reverse=True)
    filtered = client.get("/api/v1/parts", params={"lifecycle_status": "OBSOLETE"}).json()
    assert all(i["lifecycle_status"] == "OBSOLETE" for i in filtered["items"])


def test_part_detail_and_404(client) -> None:  # type: ignore[no-untyped-def]
    first = client.get("/api/v1/parts", params={"page_size": 1}).json()["items"][0]
    detail = client.get(f"/api/v1/parts/{first['part_key']}")
    assert detail.status_code == 200
    assert client.get("/api/v1/parts/NOPE").status_code == 404


def test_part_lineage_golden_record(client) -> None:  # type: ignore[no-untyped-def]
    first = client.get("/api/v1/parts", params={"page_size": 1}).json()["items"][0]
    lineage = client.get(f"/api/v1/parts/{first['part_key']}/lineage").json()
    assert lineage["members"]
    assert "description" in lineage["fields"] or "uom" in lineage["fields"]


def test_part_impact(client) -> None:  # type: ignore[no-untyped-def]
    first = client.get("/api/v1/parts", params={"page_size": 1}).json()["items"][0]
    impact = client.get(f"/api/v1/parts/{first['part_key']}/impact").json()
    assert "operational_priority" in impact
    assert "inventory_value_exposed" in impact


def test_issue_list_and_evidence(client) -> None:  # type: ignore[no-untyped-def]
    issue = _first_issue(client, severity="critical")
    assert issue["severity"] == "critical"
    evidence = client.get(f"/api/v1/issues/{issue['issue_id']}/evidence").json()
    assert len(evidence) >= 1


def test_recommendation_generation(client) -> None:  # type: ignore[no-untyped-def]
    issue = _first_issue(client)
    r = client.post(f"/api/v1/issues/{issue['issue_id']}/recommendations")
    assert r.status_code == 200
    proposal = r.json()
    assert proposal["human_review_required"] is True
    assert proposal["evidence_refs"]


def test_approval_workflow_with_audit(client) -> None:  # type: ignore[no-untyped-def]
    issue = _first_issue(client, status="DETECTED")
    r = client.post(
        f"/api/v1/issues/{issue['issue_id']}/approve",
        json={"reviewer": "darshita", "reason": "verified against source"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "APPROVED"
    # double-approve must 409
    again = client.post(
        f"/api/v1/issues/{issue['issue_id']}/approve",
        json={"reviewer": "darshita", "reason": "again"},
    )
    assert again.status_code == 409
    history = client.get(f"/api/v1/issues/{issue['issue_id']}/history").json()
    assert len(history) == 1
    assert history[0]["decision"] == "APPROVE"
    assert history[0]["before_status"] == "DETECTED"


def test_bom_graph_endpoints(client) -> None:  # type: ignore[no-untyped-def]
    # find a part that actually has BOM relationships
    import_json = client.get(
        "/api/v1/issues", params={"rule_id": "VALD-006", "page_size": 1}
    ).json()
    # fall back: query a parent from the graph rule domain via parts
    parts = client.get("/api/v1/parts", params={"page_size": 200}).json()["items"]
    graph_resp = None
    for p in parts:
        r = client.get(f"/api/v1/bom/{p['part_key']}/graph")
        if r.status_code == 200 and r.json()["edges"]:
            graph_resp = r.json()
            break
    assert graph_resp is not None, "no part with BOM found"
    assert graph_resp["nodes"] and graph_resp["edges"]
    part_id = graph_resp["root"]
    deps = client.get(f"/api/v1/bom/{part_id}/dependencies").json()
    assert deps["dependencies"]
    rev = client.get(f"/api/v1/bom/{graph_resp['edges'][0]['child']}/reverse-dependencies").json()
    assert rev["affected_assembly_count"] >= 1
    assert import_json is not None  # keep linter happy about unused variable


def test_scenario_simulation_and_retrieval(client) -> None:  # type: ignore[no-untyped-def]
    parts = client.get("/api/v1/parts", params={"page_size": 2}).json()["items"]
    r = client.post(
        "/api/v1/scenarios/merge",
        json={"duplicate_id": parts[0]["part_key"], "surviving_id": parts[1]["part_key"]},
    )
    assert r.status_code == 200
    scenario = r.json()
    assert scenario["approval_required"] is True
    fetched = client.get(f"/api/v1/scenarios/{scenario['scenario_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["scenario_type"] == "merge"


def test_analytics_endpoints(client) -> None:  # type: ignore[no-untyped-def]
    quality = client.get("/api/v1/analytics/quality").json()
    assert "enterprise_quality_score" in quality
    impact = client.get("/api/v1/analytics/business-impact").json()
    assert impact["total_inventory_value"] > 0
    remediation = client.get("/api/v1/analytics/remediation").json()
    assert "backlog" in remediation
    gov = client.get("/api/v1/analytics/ai-governance").json()
    assert gov["calls"] >= 1  # from the recommendation test


def test_no_stack_traces_in_errors(client) -> None:  # type: ignore[no-untyped-def]
    r = client.get("/api/v1/parts", params={"sort_by": "evil_column"})
    assert r.status_code == 422
    assert "Traceback" not in r.text
