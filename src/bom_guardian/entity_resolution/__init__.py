"""Explainable entity resolution: blocking, similarity features, matchers."""

from bom_guardian.entity_resolution.baseline import (
    ConfidenceBand,
    MatchCandidate,
    WeightedMatcher,
)
from bom_guardian.entity_resolution.blocking import generate_candidate_pairs
from bom_guardian.entity_resolution.features import FEATURE_NAMES, pair_features

__all__ = [
    "FEATURE_NAMES",
    "ConfidenceBand",
    "MatchCandidate",
    "WeightedMatcher",
    "generate_candidate_pairs",
    "pair_features",
]
