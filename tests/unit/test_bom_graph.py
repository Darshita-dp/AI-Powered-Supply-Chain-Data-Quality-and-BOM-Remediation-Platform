"""BOM graph tests: all required structural shapes from the build spec."""

import pandas as pd

from bom_guardian.bom_graph import BomGraph


def _graph(edges: list[tuple[str, str]], qty: float = 1.0) -> BomGraph:
    df = pd.DataFrame(
        [
            {
                "parent_part_id": p,
                "child_part_id": c,
                "quantity_per": qty,
                "bom_component_id": f"E{i}",
            }
            for i, (p, c) in enumerate(edges)
        ]
    )
    return BomGraph.from_components(df)


# A: two-root shared-component hierarchy, 4 levels deep
DEEP = _graph(
    [
        ("FG1", "SA1"),
        ("FG1", "SA2"),
        ("FG2", "SA2"),
        ("SA1", "C1"),
        ("SA1", "C2"),
        ("SA2", "C2"),
        ("SA2", "SA3"),
        ("SA3", "C3"),
        ("C3", "RAW1"),
    ]
)


def test_acyclic_bom_validates_clean() -> None:
    report = DEEP.validate()
    assert report["is_acyclic"]
    assert report["cycles"] == []
    assert report["self_references"] == []


def test_direct_cycle_detected() -> None:
    g = _graph([("A", "B"), ("B", "A")])
    cycles = g.cycles()
    assert len(cycles) == 1
    assert set(cycles[0]) == {"A", "B"}


def test_multi_level_cycle_detected() -> None:
    g = _graph([("A", "B"), ("B", "C"), ("C", "A")])
    assert not g.is_acyclic()
    assert any(set(c) == {"A", "B", "C"} for c in g.cycles())


def test_self_reference_detected() -> None:
    g = _graph([("A", "B"), ("X", "X")])
    assert g.self_references() == ["X"]
    assert g.cycles() == []  # self-refs are reported separately


def test_orphans_split_by_role() -> None:
    g = _graph([("GHOST_PARENT", "C1"), ("FG", "GHOST_CHILD")])
    orphans = g.orphans(known_part_ids={"C1", "FG"})
    assert orphans["missing_parents"] == ["GHOST_PARENT"]
    assert orphans["missing_children"] == ["GHOST_CHILD"]


def test_disconnected_components_counted() -> None:
    g = _graph([("A", "B"), ("X", "Y")])
    assert g.validate()["connected_components"] == 2


def test_roots_and_leaves() -> None:
    assert DEEP.roots() == ["FG1", "FG2"]
    assert DEEP.leaves() == ["C1", "C2", "RAW1"]


def test_deep_hierarchy_depth() -> None:
    assert DEEP.depth("FG1") == 4  # FG1 -> SA2 -> SA3 -> C3 -> RAW1
    assert DEEP.depth("C1") == 0
    assert DEEP.max_depth() == 4


def test_shared_component_reverse_dependencies() -> None:
    rev = DEEP.reverse_dependencies("C2")
    assert set(rev) == {"FG1", "FG2", "SA1", "SA2"}
    assert DEEP.affected_assembly_count("C2") == 4


def test_dependency_expansion_and_paths() -> None:
    deps = DEEP.dependencies("SA2")
    assert set(deps) == {"C2", "SA3", "C3", "RAW1"}
    paths = DEEP.paths("FG1", "RAW1")
    assert paths == [["FG1", "SA2", "SA3", "C3", "RAW1"]]


def test_expand_levels_and_quantities() -> None:
    rows = DEEP.expand("SA3")
    assert rows == [
        {"parent": "SA3", "child": "C3", "level": 1, "quantity_per": 1.0},
        {"parent": "C3", "child": "RAW1", "level": 2, "quantity_per": 1.0},
    ]


def test_centrality_ranks_shared_component_high() -> None:
    cent = DEEP.centrality(top_n=3)
    assert "SA2" in cent  # most connected node


def test_criticality_uses_demand_exposure() -> None:
    crit = DEEP.criticality("C2", demand_by_part={"FG1": 100.0, "FG2": 50.0})
    assert crit["affected_assemblies"] == 4
    assert crit["demand_quantity_exposed"] == 150.0
    assert crit["criticality_score"] > 0


def test_supplier_concentration_single_source() -> None:
    sp = pd.DataFrame(
        [
            {"part_id": "C3", "supplier_id": "S1"},
            {"part_id": "RAW1", "supplier_id": "S1"},
            {"part_id": "RAW1", "supplier_id": "S2"},
        ]
    )
    conc = DEEP.supplier_concentration("SA3", sp)
    assert conc["single_source_components"] == 1
    assert conc["single_source_ratio"] == 0.5


def test_unknown_part_is_safe() -> None:
    assert DEEP.dependencies("NOPE") == []
    assert DEEP.reverse_dependencies("NOPE") == []
    assert DEEP.paths("NOPE", "C1") == []
    assert DEEP.expand("NOPE") == []


def test_cycle_corrupted_subtree_depth_does_not_crash() -> None:
    g = _graph([("A", "B"), ("B", "C"), ("C", "B")])
    assert g.depth("A") >= 1
