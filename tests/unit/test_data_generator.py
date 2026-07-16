"""Tests for the synthetic ERP data generator (smoke profile)."""

import networkx as nx
import pandas as pd
import pytest
from data_generator.config.profiles import PROFILES, ProfileConfig
from data_generator.orchestrator import generate_all, validate_referential_integrity

TINY = ProfileConfig(name="tiny", n_parts=200, n_suppliers=20, n_plants=2, warehouses_per_plant=2)


@pytest.fixture(scope="module")
def data() -> dict[str, pd.DataFrame]:
    # patch a tiny profile in for fast tests
    PROFILES["tiny"] = TINY
    return generate_all("tiny", seed=123)


def test_all_datasets_present_and_nonempty(data) -> None:  # type: ignore[no-untyped-def]
    expected = {
        "units_of_measure",
        "product_categories",
        "plants",
        "warehouses",
        "suppliers",
        "part_master",
        "part_aliases",
        "supplier_parts",
        "bom_headers",
        "bom_components",
        "engineering_revisions",
        "engineering_change_orders",
        "part_substitutions",
        "part_supersessions",
        "inventory_snapshots",
        "purchase_orders",
        "purchase_order_lines",
        "future_demand",
        "production_orders",
        "standard_cost_history",
        "lead_time_history",
        "supplier_quotes",
    }
    assert set(data.keys()) == expected
    for name in expected:
        assert len(data[name]) > 0, f"{name} is empty"


def test_referential_integrity_clean_baseline(data) -> None:  # type: ignore[no-untyped-def]
    assert validate_referential_integrity(data) == []


def test_baseline_bom_is_acyclic_and_multilevel(data) -> None:  # type: ignore[no-untyped-def]
    comps = data["bom_components"]
    g = nx.DiGraph()
    g.add_edges_from(comps[["parent_part_id", "child_part_id"]].itertuples(index=False))
    assert nx.is_directed_acyclic_graph(g)
    # multi-level: at least one path of length >= 2 (assembly -> subassembly -> component)
    depth = nx.dag_longest_path_length(g)
    assert depth >= 2, f"BOM should be multi-level, max depth was {depth}"


def test_generation_is_deterministic() -> None:
    PROFILES["tiny"] = TINY
    a = generate_all("tiny", seed=99)
    b = generate_all("tiny", seed=99)
    for name in a:
        pd.testing.assert_frame_equal(a[name], b[name])


def test_different_seeds_differ() -> None:
    PROFILES["tiny"] = TINY
    a = generate_all("tiny", seed=1)
    b = generate_all("tiny", seed=2)
    assert not a["part_master"]["source_part_number"].equals(b["part_master"]["source_part_number"])


def test_part_lifecycle_statuses_present(data) -> None:  # type: ignore[no-untyped-def]
    statuses = set(data["part_master"]["lifecycle_status"].unique())
    assert {"ACTIVE", "BLOCKED", "OBSOLETE"} <= statuses


def test_multiple_source_systems(data) -> None:  # type: ignore[no-untyped-def]
    assert data["part_master"]["source_system"].nunique() >= 3


def test_po_line_values_consistent(data) -> None:  # type: ignore[no-untyped-def]
    lines = data["purchase_order_lines"]
    expected = lines["order_qty"] * lines["unit_price"]
    # allow for rounding differences of at most one cent
    assert (lines["line_value"] - expected).abs().max() <= 0.01
