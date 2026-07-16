"""Train + evaluate ML duplicate matchers and compare with the weighted baseline.

Usage:
    python scripts/train_entity_resolution.py [--profile smoke] [--seed 20260716]

Writes:
    evaluation/entity_resolution/ml_<profile>.json   (measured metrics)
    models/artifacts/er_gradient_boosting.joblib     (git-ignored)
    models/artifacts/er_logistic_regression.joblib   (git-ignored)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
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
    from bom_guardian.entity_resolution.evaluate import evaluate_matches
    from bom_guardian.entity_resolution.ml import MLMatcherTrainer, build_pair_dataset

    clean = generate_all(args.profile, args.seed)
    injected = inject_all(clean, seed=args.seed, rate=args.rate)
    parts, gt = injected.data["part_master"], injected.ground_truth

    # baseline on the same data for objective comparison
    matches = WeightedMatcher().find_matches(parts)
    baseline = {
        "recommend_band": evaluate_matches(matches, gt, ConfidenceBand.RECOMMEND),
        "review_band": evaluate_matches(matches, gt, ConfidenceBand.REVIEW),
    }

    dataset = build_pair_dataset(parts, gt)
    trainer = MLMatcherTrainer(seed=args.seed)
    ml_report = trainer.train_and_evaluate(dataset)

    artifacts = REPO / "models" / "artifacts"
    for name in ("logistic_regression", "gradient_boosting"):
        trainer.save(name, artifacts / f"er_{name}.joblib")

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "profile": args.profile,
        "seed": args.seed,
        "inject_rate": args.rate,
        "note": (
            "Measured on synthetic data with injected ground truth. Baseline metrics "
            "cover ALL labeled pairs; ML metrics are on the held-out group-aware test "
            "split of blocked candidate pairs — comparable in method, not identical "
            "in denominator."
        ),
        "weighted_baseline": baseline,
        "ml": ml_report,
    }
    out = REPO / "evaluation" / "entity_resolution" / f"ml_{args.profile}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    print(f"Report written to {out}")
    for name, m in ml_report["models"].items():
        print(f"{name}: P={m['precision']} R={m['recall']} F1={m['f1']} t={m['threshold']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
