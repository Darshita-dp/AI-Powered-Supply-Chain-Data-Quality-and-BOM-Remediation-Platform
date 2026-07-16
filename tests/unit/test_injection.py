"""Tests proving controlled issue injection is correct and fully labeled."""

import networkx as nx
import pandas as pd
import pytest
from data_generator.config.profiles import PROFILES, ProfileConfig
from data_generator.injectors import ISSUE_TYPES, inject_all
from data_generator.orchestrator import generate_all

TINY = ProfileConfig(name="tiny", n_parts=400, n_suppliers=40, n_plants=2, warehouses_per_plant=2)


@pytest.fixture(scope="module")
def clean() -> dict[str, pd.DataFrame]:
    PROFILES["tiny"] = TINY
    return generate_all("tiny", seed=777)


@pytest.fixture(scope="module")
def result(clean):  # type: ignore[no-untyped-def]
    return inject_all(clean, seed=777, rate=0.03)


def test_all_25_issue_types_injected(result) -> None:  # type: ignore[no-untyped-def]
    assert len(ISSUE_TYPES) == 25
    injected_types = set(result.ground_truth["issue_type"].unique())
    assert injected_types == set(ISSUE_TYPES)


def test_every_injection_has_a_label(result) -> None:  # type: ignore[no-untyped-def]
    gt = result.ground_truth
    required = ["injection_id", "issue_type", "dataset", "record_id", "difficulty", "seed"]
    for col in required:
        assert gt[col].notna().all(), f"{col} has nulls"
    assert gt["injection_id"].is_unique


def test_difficulty_levels_present(result) -> None:  # type: ignore[no-untyped-def]
    assert {"easy", "medium"} <= set(result.ground_truth["difficulty"].unique())


def test_clean_baseline_not_mutated(clean, result) -> None:  # type: ignore[no-untyped-def]
    # inject_all must work on copies: the clean data still has no ghost parts
    assert not clean["part_master"]["part_id"].str.startswith("PRT9").any()
    assert result.data["part_master"]["part_id"].str.startswith("PRT9").any()


def test_duplicates_reference_real_originals(clean, result) -> None:  # type: ignore[no-untyped-def]
    gt = result.ground_truth
    dups = gt[gt["issue_type"].isin(["exact_duplicate_part", "fuzzy_duplicate_part"])]
    originals = set(clean["part_master"]["part_id"])
    assert dups["correct_matching_entity"].isin(originals).all()


def test_injected_bom_contains_cycles(result) -> None:  # type: ignore[no-untyped-def]
    comps = result.data["bom_components"]
    g = nx.DiGraph()
    g.add_edges_from(comps[["parent_part_id", "child_part_id"]].itertuples(index=False))
    assert not nx.is_directed_acyclic_graph(g)


def test_orphans_reference_missing_parts(result) -> None:  # type: ignore[no-untyped-def]
    gt = result.ground_truth
    part_ids = set(result.data["part_master"]["part_id"])
    orphan_labels = gt[gt["issue_type"] == "orphan_bom_component"]
    comps = result.data["bom_components"].set_index("bom_component_id")
    for _, lbl in orphan_labels.iterrows():
        assert comps.loc[lbl["record_id"], "child_part_id"] not in part_ids


def test_field_corruptions_are_recorded_accurately(result) -> None:  # type: ignore[no-untyped-def]
    gt = result.ground_truth
    uom_labels = gt[gt["issue_type"] == "invalid_uom"]
    parts = result.data["part_master"].set_index("part_id")
    for _, lbl in uom_labels.iterrows():
        assert str(parts.loc[lbl["record_id"], "uom"]) == lbl["injected_value"]
        assert lbl["correct_value"] == lbl["original_value"]


def test_injection_is_deterministic(clean) -> None:  # type: ignore[no-untyped-def]
    a = inject_all(clean, seed=42, rate=0.03)
    b = inject_all(clean, seed=42, rate=0.03)
    pd.testing.assert_frame_equal(a.ground_truth, b.ground_truth)
    for name in a.data:
        pd.testing.assert_frame_equal(a.data[name], b.data[name])
