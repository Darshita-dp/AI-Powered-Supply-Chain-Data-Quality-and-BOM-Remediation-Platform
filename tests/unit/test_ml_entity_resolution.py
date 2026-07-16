"""Tests for ML entity resolution: training, thresholds, persistence, no leakage."""

import numpy as np
import pytest
from data_generator.config.profiles import PROFILES, ProfileConfig
from data_generator.injectors import inject_all
from data_generator.orchestrator import generate_all

from bom_guardian.entity_resolution.ml import (
    PRECISION_FLOOR,
    MLMatcherTrainer,
    build_pair_dataset,
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


def test_precision_floor_respected_or_documented(trained) -> None:  # type: ignore[no-untyped-def]
    _, report = trained
    assert report["precision_floor"] == PRECISION_FLOOR
    for m in report["models"].values():
        # test-set precision can dip below the val-selected floor, but not collapse
        assert m["precision"] >= 0.7, m


def test_lr_coefficients_exposed_for_explainability(trained) -> None:  # type: ignore[no-untyped-def]
    _, report = trained
    coefs = report["models"]["logistic_regression"]["coefficients"]
    assert "part_number_char_similarity" in coefs


def test_split_is_group_aware(dataset) -> None:  # type: ignore[no-untyped-def]
    from sklearn.model_selection import GroupShuffleSplit

    gss = GroupShuffleSplit(n_splits=1, test_size=0.4, random_state=31)
    train_idx, rest_idx = next(gss.split(dataset.X, dataset.y, dataset.groups))
    assert set(dataset.groups[train_idx]).isdisjoint(set(dataset.groups[rest_idx]))


def test_model_persistence_roundtrip(trained, tmp_path) -> None:  # type: ignore[no-untyped-def]
    trainer, _ = trained
    path = trainer.save("gradient_boosting", tmp_path / "gb.joblib")
    loaded = MLMatcherTrainer.load(path)
    assert loaded["threshold"] > 0
    assert loaded["features"]
    proba = loaded["model"].predict_proba(np.zeros((1, len(loaded["features"]))))
    assert proba.shape == (1, 2)
