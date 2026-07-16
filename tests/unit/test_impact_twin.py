"""Quality Impact Twin tests: blast radius numbers and non-mutating scenarios."""

import pandas as pd
import pytest

from bom_guardian.bom_graph import BomGraph
from bom_guardian.impact_twin import ImpactTwin, ScenarioSimulator
from bom_guardian.warehouse import LocalWarehouse


@pytest.fixture()
def fixture_data() -> dict:
    comps = pd.DataFrame(
        [
            {
                "parent_part_id": "FG1",
                "child_part_id": "SA1",
                "quantity_per": 1,
                "bom_component_id": "B1",
            },
            {
                "parent_part_id": "SA1",
                "child_part_id": "C1",
                "quantity_per": 2,
                "bom_component_id": "B2",
            },
            {
                "parent_part_id": "SA1",
                "child_part_id": "C2",
                "quantity_per": 4,
                "bom_component_id": "B3",
            },
            {
                "parent_part_id": "FG2",
                "child_part_id": "C1",
                "quantity_per": 1,
                "bom_component_id": "B4",
            },
        ]
    )
    parts = pd.DataFrame(
        [
            {
                "part_id": "FG1",
                "description": "Finished good",
                "lifecycle_status": "ACTIVE",
                "uom": "EA",
                "standard_cost": 1000.0,
                "primary_plant": "PL01",
            },
            {
                "part_id": "FG2",
                "description": "Finished good 2",
                "lifecycle_status": "ACTIVE",
                "uom": "EA",
                "standard_cost": 800.0,
                "primary_plant": "PL02",
            },
            {
                "part_id": "SA1",
                "description": "Subassembly",
                "lifecycle_status": "ACTIVE",
                "uom": "EA",
                "standard_cost": 200.0,
                "primary_plant": "PL01",
            },
            {
                "part_id": "C1",
                "description": "Shared component",
                "lifecycle_status": "ACTIVE",
                "uom": "EA",
                "standard_cost": 10.0,
                "primary_plant": "PL01",
            },
            {
                "part_id": "C2",
                "description": "Obsolete component",
                "lifecycle_status": "OBSOLETE",
                "uom": "EA",
                "standard_cost": 5.0,
                "primary_plant": "PL01",
            },
            {
                "part_id": "C3",
                "description": "Replacement component",
                "lifecycle_status": "ACTIVE",
                "uom": "EA",
                "standard_cost": 6.0,
                "primary_plant": "PL01",
            },
            {
                "part_id": "C1_DUP",
                "description": "Shared component copy",
                "lifecycle_status": "ACTIVE",
                "uom": "EA",
                "standard_cost": 10.5,
                "primary_plant": "PL02",
            },
        ]
    )
    inventory = pd.DataFrame(
        [
            {"part_id": "C1", "on_hand_value": 500.0},
            {"part_id": "SA1", "on_hand_value": 2000.0},
            {"part_id": "FG1", "on_hand_value": 10000.0},
        ]
    )
    demand = pd.DataFrame(
        [
            {"part_id": "FG1", "demand_qty": 100.0},
            {"part_id": "FG2", "demand_qty": 50.0},
        ]
    )
    po_lines = pd.DataFrame([{"part_id": "C1", "line_value": 1500.0}])
    production = pd.DataFrame([{"part_id": "FG1", "status": "RELEASED"}])
    supplier_parts = pd.DataFrame(
        [
            {"part_id": "C1", "supplier_id": "S1"},
            {"part_id": "C2", "supplier_id": "S2"},
            {"part_id": "C1_DUP", "supplier_id": "S3"},
        ]
    )
    graph = BomGraph.from_components(comps)
    twin = ImpactTwin(
        graph=graph,
        parts=parts,
        inventory=inventory,
        future_demand=demand,
        po_lines=po_lines,
        production_orders=production,
        supplier_parts=supplier_parts,
    )
    return {
        "twin": twin,
        "parts": parts,
        "comps": comps,
        "inventory": inventory,
        "demand": demand,
        "supplier_parts": supplier_parts,
    }


def test_blast_radius_counts_upstream_exposure(fixture_data) -> None:  # type: ignore[no-untyped-def]
    r = fixture_data["twin"].blast_radius("C1")
    assert r["affected_parent_assemblies"] == 3  # SA1, FG1, FG2
    assert r["future_demand_qty_exposed"] == 150.0  # FG1 + FG2 demand
    assert r["inventory_value_exposed"] == 12500.0  # C1 + SA1 + FG1
    assert r["po_value_exposed"] == 1500.0
    assert r["production_orders_affected"] == 1
    assert r["plants_affected"] == 2
    assert r["operational_priority"] > 0


def test_leaf_with_no_usage_has_minimal_radius(fixture_data) -> None:  # type: ignore[no-untyped-def]
    r = fixture_data["twin"].blast_radius("C3")
    assert r["affected_parent_assemblies"] == 0
    assert r["future_demand_qty_exposed"] == 0.0


def test_merge_scenario_before_after(fixture_data) -> None:  # type: ignore[no-untyped-def]
    sim = ScenarioSimulator(fixture_data["twin"])
    result = sim.merge_parts("C1_DUP", "C1")
    assert result.scenario_type == "merge"
    assert result.before["duplicate_record"]["part_id"] == "C1_DUP"
    assert result.resolved_rules == ["UNIQ-002"]
    assert result.approval_required is True


def test_merge_into_obsolete_part_warns(fixture_data) -> None:  # type: ignore[no-untyped-def]
    sim = ScenarioSimulator(fixture_data["twin"])
    result = sim.merge_parts("C1", "C2")  # C2 is OBSOLETE
    assert any("non-active" in w for w in result.new_warnings)


def test_component_replacement_resolves_obsolete_rule(fixture_data) -> None:  # type: ignore[no-untyped-def]
    sim = ScenarioSimulator(fixture_data["twin"])
    result = sim.component_replacement("SA1", "C2", "C3")
    assert result.after["relationships_replaced"] == 1
    assert "XFLD-004" in result.resolved_rules
    assert result.new_warnings == []


def test_replacement_with_blocked_part_warns(fixture_data) -> None:  # type: ignore[no-untyped-def]
    parts = fixture_data["parts"]
    parts.loc[parts["part_id"] == "C3", "lifecycle_status"] = "BLOCKED"
    sim = ScenarioSimulator(fixture_data["twin"])
    result = sim.component_replacement("SA1", "C2", "C3")
    assert any("BLOCKED" in w for w in result.new_warnings)


def test_field_correction_resolves_and_warns(fixture_data) -> None:  # type: ignore[no-untyped-def]
    sim = ScenarioSimulator(fixture_data["twin"])
    good = sim.field_correction("C1", "uom", "KG")
    assert "VALD-001" in good.resolved_rules
    bad = sim.field_correction("C1", "uom", "PCS")
    assert any("governed list" in w for w in bad.new_warnings)


def test_simulation_never_mutates_baseline(fixture_data) -> None:  # type: ignore[no-untyped-def]
    twin = fixture_data["twin"]
    comps_before = fixture_data["comps"].copy()
    parts_before = fixture_data["parts"].copy()
    sp_before = fixture_data["supplier_parts"].copy()
    edges_before = sorted(twin.graph.g.edges)

    sim = ScenarioSimulator(twin)
    sim.merge_parts("C1_DUP", "C1")
    sim.component_replacement("SA1", "C2", "C3")
    sim.field_correction("C1", "uom", "KG")

    pd.testing.assert_frame_equal(fixture_data["comps"], comps_before)
    pd.testing.assert_frame_equal(fixture_data["parts"], parts_before)
    pd.testing.assert_frame_equal(fixture_data["supplier_parts"], sp_before)
    assert sorted(twin.graph.g.edges) == edges_before


def test_scenarios_persisted_separately(fixture_data) -> None:  # type: ignore[no-untyped-def]
    with LocalWarehouse(":memory:") as wh:
        sim = ScenarioSimulator(fixture_data["twin"], warehouse=wh)
        result = sim.merge_parts("C1_DUP", "C1")
        rows = wh.query("SELECT * FROM quality.scenarios")
        assert len(rows) == 1
        assert rows.iloc[0]["scenario_id"] == result.scenario_id
        # scenario persistence must not create/replace core tables
        assert wh.tables("core") == []
