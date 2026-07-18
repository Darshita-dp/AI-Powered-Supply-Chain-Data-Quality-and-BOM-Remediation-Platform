"""Tests for ML entity resolution: training, thresholds, persistence, no leakage."""

import numpy as np
import pytest
from data_generator.config.profiles import PROFILES, ProfileConfig
from data_generator.injectors import inject_all
from data_generator.orchestrator import generate_all

from bom_guardian.entity_resolution.ml import (
    PRECISION_FLOOR,
    MLMatcherTrainer,
    PairDataset,
    _connected_component_groups,
    build_pair_dataset,
    evaluate_across_seeds,
)

TINY = ProfileConfig(name="tiny", n_parts=500, n_suppliers=40, n_plants=2, warehouses_per_plant=1)


@pytest.fixture(scope="module")
def dataset():  # type: ignore[no-untyped-def]
    PROFILES["tiny"] = TINY
    clean = generate_all("tiny", seed=31)
    injected = inject_all(clean, seed=31, rate=0.05)
    return build_pair_dataset(injected.data["part_master"], injected.ground_truth)


@pytest.fixture(scope="module")
def trained(dataset):  # type: ignore[no-untyped-def]
    trainer = MLMatcherTrainer(seed=31)
    report = trainer.train_and_evaluate(dataset)
    return trainer, report


def test_dataset_has_positives_and_negatives(dataset) -> None:  # type: ignore[no-untyped-def]
    assert dataset.y.sum() > 5
    assert (dataset.y == 0).sum() > dataset.y.sum()


def test_both_models_trained_with_metrics(trained) -> None:  # type: ignore[no-untyped-def]
    _, report = trained
    for name in ("logistic_regression", "gradient_boosting"):
        m = report["models"][name]
        assert set(m) >= {"precision", "recall", "f1", "threshold", "confusion_matrix"}
        assert 0.0 <= m["precision"] <= 1.0


def test_precision_floor_configured_and_metrics_valid(trained) -> None:  # type: ignore[no-untyped-def]
    _, report = trained
    assert report["precision_floor"] == PRECISION_FLOOR
    for m in report["models"].values():
        # Threshold selection targets precision >= floor on validation, but the small
        # held-out test fold can move the realized precision either way. We assert only
        # that metrics are well-formed — H2 stops pretending a fixed floor always holds.
        assert 0.0 <= m["precision"] <= 1.0
        assert 0.0 <= m["recall"] <= 1.0
        assert 0.0 <= m["f1"] <= 1.0


def test_lr_coefficients_exposed_for_explainability(trained) -> None:  # type: ignore[no-untyped-def]
    _, report = trained
    coefs = report["models"]["logistic_regression"]["coefficients"]
    assert "part_number_char_similarity" in coefs


def test_connected_component_keeps_chain_in_one_group() -> None:
    """A-B, B-C, C-D must all land in a single connected component (one fold)."""
    pairs = [("A", "B"), ("B", "C"), ("C", "D"), ("X", "Y")]
    groups = _connected_component_groups(pairs)
    assert groups["A"] == groups["B"] == groups["C"] == groups["D"]
    assert groups["X"] == groups["Y"]
    assert groups["A"] != groups["X"]  # disjoint chains are different components


def test_split_is_entity_disjoint(dataset) -> None:  # type: ignore[no-untyped-def]
    """The real assertion: no part id appears in more than one fold."""
    trainer = MLMatcherTrainer(seed=31)
    train_idx, val_idx, test_idx = trainer._split_indices(dataset)
    tr = trainer._parts_in(dataset, train_idx)
    va = trainer._parts_in(dataset, val_idx)
    te = trainer._parts_in(dataset, test_idx)
    assert tr.isdisjoint(va)
    assert tr.isdisjoint(te)
    assert va.isdisjoint(te)


def test_leaky_dataset_is_rejected() -> None:
    """If a group spanned folds, the disjointness assertion must fire."""
    # Two candidate pairs sharing part 'B' -> same component; forcing them into
    # different folds (by corrupting groups) must raise.
    ds = PairDataset(
        X=np.zeros((2, 1)),
        y=np.array([1, 0]),
        groups=np.array([0, 1]),  # WRONG on purpose: B is in both rows but different groups
        parts_a=np.array(["A", "B"]),
        parts_b=np.array(["B", "C"]),
        pairs=[("A", "B"), ("B", "C")],
        difficulty=[None, None],
        n_truth_pairs=1,
        n_truth_pairs_as_candidates=1,
    )
    trainer = MLMatcherTrainer(seed=1)
    with pytest.raises(AssertionError, match="entity leakage"):
        trainer._assert_entity_disjoint(ds, np.array([0]), np.array([], dtype=int), np.array([1]))


def test_report_includes_split_composition_and_candidate_recall(trained) -> None:  # type: ignore[no-untyped-def]
    _, report = trained
    split = report["split"]
    assert split["entity_disjoint_asserted"] is True
    for fold in ("train", "validation", "test"):
        comp = split[fold]
        assert comp["positive_pairs"] + comp["negative_pairs"] == comp["pairs"]
        assert comp["unique_parts"] > 0
    cg = report["candidate_generation"]
    assert 0.0 <= cg["candidate_generation_recall"] <= 1.0
    assert cg["produced_as_candidates"] <= cg["labeled_duplicate_pairs"]


def test_multi_seed_evaluation_reports_dispersion(dataset) -> None:  # type: ignore[no-untyped-def]
    agg = evaluate_across_seeds(dataset, seeds=[1, 7, 13, 21, 31])
    assert agg["n_runs"] == 5
    gb = agg["aggregated"]["gradient_boosting"]["recall"]
    assert 0.0 <= gb["mean"] <= 1.0
    assert gb["std"] >= 0.0
    assert len(gb["values"]) == 5


def test_model_persistence_roundtrip(trained, tmp_path) -> None:  # type: ignore[no-untyped-def]
    trainer, _ = trained
    path = trainer.save("gradient_boosting", tmp_path / "gb.joblib")
    loaded = MLMatcherTrainer.load(path)
    assert loaded["threshold"] > 0
    assert loaded["features"]
    proba = loaded["model"].predict_proba(np.zeros((1, len(loaded["features"]))))
    assert proba.shape == (1, 2)
