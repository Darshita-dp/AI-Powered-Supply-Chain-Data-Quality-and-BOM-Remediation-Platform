"""Weighted deterministic matching baseline.

Transparent linear scoring over interpretable features with configurable,
precision-favoring thresholds and an explicit abstain band. Never auto-merges:
output is candidate matches with evidence for downstream review.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import pandas as pd

from bom_guardian.entity_resolution.blocking import generate_candidate_pairs
from bom_guardian.entity_resolution.features import pair_features
from bom_guardian.observability import get_logger

# Weights sum to 1.0; identifier evidence dominates by design.
DEFAULT_WEIGHTS: dict[str, float] = {
    "part_number_exact": 0.22,
    "part_number_normalized_match": 0.20,
    "part_number_char_similarity": 0.14,
    "description_token_jaccard": 0.12,
    "description_char_similarity": 0.08,
    "mpn_match": 0.12,
    "uom_compatible": 0.02,
    "category_match": 0.04,
    "cost_proximity": 0.05,
    "source_system_differs": 0.0,  # informational only
    "lead_time_proximity": 0.01,
}

RECOMMEND_THRESHOLD = 0.72
REVIEW_THRESHOLD = 0.55


class ConfidenceBand(StrEnum):
    RECOMMEND = "high_confidence_recommendation"
    REVIEW = "human_review_required"
    ABSTAIN = "unresolved"


@dataclass
class MatchCandidate:
    part_id_a: str
    part_id_b: str
    score: float
    band: ConfidenceBand
    features: dict[str, float]

    def evidence(self) -> list[str]:
        """Human-readable reasons, strongest first."""
        contribs = sorted(
            ((DEFAULT_WEIGHTS.get(k, 0) * v, k, v) for k, v in self.features.items()),
            reverse=True,
        )
        return [f"{name}={value:.2f}" for contrib, name, value in contribs if contrib > 0.01]


class WeightedMatcher:
    """Deterministic weighted-sum matcher over blocked candidate pairs."""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        recommend_threshold: float = RECOMMEND_THRESHOLD,
        review_threshold: float = REVIEW_THRESHOLD,
    ) -> None:
        self.weights = weights or DEFAULT_WEIGHTS
        self.recommend_threshold = recommend_threshold
        self.review_threshold = review_threshold
        self._log = get_logger("weighted_matcher")

    def score_pair(self, a: pd.Series, b: pd.Series) -> MatchCandidate:
        feats = pair_features(a, b)
        score = sum(self.weights.get(k, 0.0) * v for k, v in feats.items())
        if score >= self.recommend_threshold:
            band = ConfidenceBand.RECOMMEND
        elif score >= self.review_threshold:
            band = ConfidenceBand.REVIEW
        else:
            band = ConfidenceBand.ABSTAIN
        return MatchCandidate(a["part_id"], b["part_id"], round(score, 4), band, feats)

    def find_matches(
        self, parts: pd.DataFrame, min_band: ConfidenceBand = ConfidenceBand.REVIEW
    ) -> list[MatchCandidate]:
        """Run blocking + scoring; return candidates at or above `min_band`."""
        pairs = generate_candidate_pairs(parts)
        by_id = parts.set_index("part_id", drop=False)
        results: list[MatchCandidate] = []
        keep_review = min_band != ConfidenceBand.RECOMMEND
        for id_a, id_b in pairs:
            cand = self.score_pair(by_id.loc[id_a], by_id.loc[id_b])
            if cand.band == ConfidenceBand.RECOMMEND or (
                keep_review and cand.band == ConfidenceBand.REVIEW
            ):
                results.append(cand)
        self._log.info(
            "matching_complete",
            candidate_pairs=len(pairs),
            matches=len(results),
            parts=len(parts),
        )
        return sorted(results, key=lambda c: c.score, reverse=True)
