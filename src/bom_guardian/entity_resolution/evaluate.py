"""Evaluation of entity resolution against injected ground truth.

Ground truth: duplicate labels map each injected duplicate part_id to its
correct original (correct_matching_entity). A predicted pair is a true positive
when it links a duplicate to exactly its labeled original.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from bom_guardian.entity_resolution.baseline import ConfidenceBand, MatchCandidate


def _truth_pairs(ground_truth: pd.DataFrame) -> dict[tuple[str, str], str]:
    """(a, b) sorted pair -> difficulty, for duplicate-part labels."""
    dups = ground_truth[
        ground_truth["issue_type"].isin(["exact_duplicate_part", "fuzzy_duplicate_part"])
    ]
    out: dict[tuple[str, str], str] = {}
    for _, row in dups.iterrows():
        a, b = sorted([str(row["record_id"]), str(row["correct_matching_entity"])])
        out[(a, b)] = str(row["difficulty"])
    return out


def evaluate_matches(
    candidates: list[MatchCandidate],
    ground_truth: pd.DataFrame,
    band: ConfidenceBand = ConfidenceBand.RECOMMEND,
) -> dict:
    """Precision/recall/F1 overall and by difficulty for a confidence band."""
    truth = _truth_pairs(ground_truth)
    predicted = {
        tuple(sorted([c.part_id_a, c.part_id_b]))
        for c in candidates
        if band == ConfidenceBand.REVIEW or c.band == ConfidenceBand.RECOMMEND
    }
    tp_pairs = predicted & set(truth)
    fp = len(predicted - set(truth))
    fn_pairs = set(truth) - predicted

    precision = len(tp_pairs) / len(predicted) if predicted else 0.0
    recall = len(tp_pairs) / len(truth) if truth else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    by_difficulty: dict[str, dict] = {}
    for diff in ("easy", "medium", "hard"):
        pairs_d = {p for p, d in truth.items() if d == diff}
        if not pairs_d:
            continue
        tp_d = len(pairs_d & predicted)
        by_difficulty[diff] = {
            "labeled": len(pairs_d),
            "found": tp_d,
            "recall": round(tp_d / len(pairs_d), 4),
        }

    return {
        "band": band.value,
        "predicted_pairs": len(predicted),
        "labeled_duplicate_pairs": len(truth),
        "true_positives": len(tp_pairs),
        "false_positives": fp,
        "false_negatives": len(fn_pairs),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "recall_by_difficulty": by_difficulty,
    }


def write_report(
    metrics: dict, path: Path, model_name: str = "weighted_baseline", extra: dict | None = None
) -> Path:
    """Persist a reproducible evaluation artifact."""
    payload = {
        "model": model_name,
        "generated_at": datetime.now(UTC).isoformat(),
        "note": (
            "Measured against injected ground-truth labels on synthetic data; "
            "reproducible via tests/data_quality and scripts/run_local_pipeline.py."
        ),
        "metrics": metrics,
        **(extra or {}),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
    return path
