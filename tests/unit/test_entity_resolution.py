"""Entity-resolution baseline tests, evaluated against injected ground truth."""

import pandas as pd
import pytest
from data_generator.config.profiles import PROFILES, ProfileConfig
from data_generator.injectors import inject_all
from data_generator.orchestrator import generate_all

from bom_guardian.entity_resolution import (
    ConfidenceBand,
    WeightedMatcher,
    generate_candidate_pairs,
    pair_features,
)
from bom_guardian.entity_resolution.baseline import DEFAULT_WEIGHTS
from bom_guardian.entity_resolution.evaluate import evaluate_matches

TINY = ProfileConfig(name="tiny", n_parts=350, n_suppliers=30, n_plants=2, warehouses_per_plant=1)


@pytest.fixture(scope="module")
def injected():  # type: ignore[no-untyped-def]
    PROFILES["tiny"] = TINY
    clean = generate_all("tiny", seed=21)
    return inject_all(clean, seed=21, rate=0.04)


@pytest.fixture(scope="module")
def matches(injected):  # type: ignore[no-untyped-def]
    return WeightedMatcher().find_matches(injected.data["part_master"])


def test_weights_sum_to_one() -> None:
    assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-9


def test_blocking_reduces_pair_space(injected) -> None:  # type: ignore[no-untyped-def]
    parts = injected.data["part_master"]
    pairs = generate_candidate_pairs(parts)
    all_pairs = len(parts) * (len(parts) - 1) / 2
    assert 0 < len(pairs) < all_pairs * 0.25


def test_identical_records_score_near_one() -> None:
    row = pd.Series(
        {
            "part_id": "A",
            "source_part_number": "FAS-123456",
            "description": "STAINLESS BOLT M3X8",
            "manufacturer_part_number": "MPN-11112222",
            "uom": "EA",
            "category": "FASTENERS",
            "standard_cost": 1.25,
            "source_system": "SAP_ECC",
            "lead_time_days": 10,
        }
    )
    other = row.copy()
    other["part_id"] = "B"
    cand = WeightedMatcher().score_pair(row, other)
    assert cand.score > 0.9
    assert cand.band is ConfidenceBand.RECOMMEND


def test_unrelated_records_abstain() -> None:
    a = pd.Series(
        {
            "part_id": "A",
            "source_part_number": "FAS-111111",
            "description": "STAINLESS BOLT M3X8",
            "manufacturer_part_number": "MPN-1",
            "uom": "EA",
            "category": "FASTENERS",
            "standard_cost": 0.5,
            "source_system": "SAP_ECC",
            "lead_time_days": 5,
        }
    )
    b = pd.Series(
        {
            "part_id": "B",
            "source_part_number": "MOT-999999",
            "description": "INDUSTRIAL PUMP 48V",
            "manufacturer_part_number": "MPN-2",
            "uom": "EA",
            "category": "MOTORS_ACTUATORS",
            "standard_cost": 900.0,
            "source_system": "PLM_TEAMCENTER",
            "lead_time_days": 60,
        }
    )
    cand = WeightedMatcher().score_pair(a, b)
    assert cand.band is ConfidenceBand.ABSTAIN


def test_features_are_all_named() -> None:
    from bom_guardian.entity_resolution import FEATURE_NAMES

    a = pd.Series({"part_id": "A", "source_part_number": "X-1", "description": "BOLT"})
    b = pd.Series({"part_id": "B", "source_part_number": "X-1", "description": "BOLT"})
    feats = pair_features(a, b)
    assert set(feats.keys()) == set(FEATURE_NAMES)
    assert all(0.0 <= v <= 1.0 for v in feats.values())


def test_recommend_band_is_precision_favoring(injected, matches) -> None:  # type: ignore[no-untyped-def]
    metrics = evaluate_matches(matches, injected.ground_truth, ConfidenceBand.RECOMMEND)
    assert metrics["predicted_pairs"] > 0
    assert metrics["precision"] >= 0.9, metrics
    # exact duplicates must essentially all be recovered
    assert metrics["recall_by_difficulty"].get("easy", {}).get("recall", 0) >= 0.8, metrics


def test_review_band_improves_recall(injected, matches) -> None:  # type: ignore[no-untyped-def]
    rec = evaluate_matches(matches, injected.ground_truth, ConfidenceBand.RECOMMEND)
    rev = evaluate_matches(matches, injected.ground_truth, ConfidenceBand.REVIEW)
    assert rev["recall"] >= rec["recall"]


def test_candidates_carry_evidence(matches) -> None:  # type: ignore[no-untyped-def]
    assert matches, "expected at least one match candidate"
    top = matches[0]
    assert top.evidence(), "match must expose human-readable evidence"
    assert isinstance(top.features, dict)
