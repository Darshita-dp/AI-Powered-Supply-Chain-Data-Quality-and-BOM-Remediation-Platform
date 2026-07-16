"""Reproducible ER evaluation: smoke profile, injected duplicates, baseline matcher.

Usage:
    python scripts/evaluate_entity_resolution.py [--profile smoke] [--seed 20260716]

Writes evaluation/entity_resolution/baseline_<profile>.json.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="smoke")
    parser.add_argument("--seed", type=int, default=20260716)
    parser.add_argument("--rate", type=float, default=0.02)
    args = parser.parse_args()

    from data_generator.injectors import inject_all
    from data_generator.orchestrator import generate_all

    from bom_guardian.entity_resolution import ConfidenceBand, WeightedMatcher
    from bom_guardian.entity_resolution.evaluate import evaluate_matches, write_report

    clean = generate_all(args.profile, args.seed)
    result = inject_all(clean, seed=args.seed, rate=args.rate)
    matches = WeightedMatcher().find_matches(result.data["part_master"])

    recommend = evaluate_matches(matches, result.ground_truth, ConfidenceBand.RECOMMEND)
    review = evaluate_matches(matches, result.ground_truth, ConfidenceBand.REVIEW)
    out = write_report(
        {"recommend_band": recommend, "review_band": review},
        REPO / "evaluation" / "entity_resolution" / f"baseline_{args.profile}.json",
        extra={"profile": args.profile, "seed": args.seed, "inject_rate": args.rate},
    )
    print(f"Report written to {out}")
    print(
        f"recommend: P={recommend['precision']} R={recommend['recall']} F1={recommend['f1']} | "
        f"review: P={review['precision']} R={review['recall']} F1={review['f1']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
