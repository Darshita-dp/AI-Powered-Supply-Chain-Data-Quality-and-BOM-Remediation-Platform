"""Train + evaluate ML duplicate matchers, leakage-safe, with a dispersion band.

Usage:
    python scripts/train_entity_resolution.py [--n-parts 4000] [--rate 0.05] [--seed 20260716]

Evaluation is entity-disjoint (connected-component grouping) and repeated across
several split seeds so the reported precision/recall/F1 carry a mean ± std band
instead of a single fragile point estimate. Also reports candidate-generation recall
so model recall is not mistaken for end-to-end recall.

Writes:
    evaluation/entity_resolution/ml_eval.json        (measured metrics)
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

# split seeds for the dispersion band (dataset is fixed; only the split varies)
SPLIT_SEEDS = [1, 7, 13, 21, 31]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--n-parts",
        type=int,
        default=4000,
        help="Larger population than smoke so the labeled duplicate set is meaningful",
    )
    parser.add_argument("--rate", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=20260716, help="Data-generation seed")
    args = parser.parse_args()

    from data_generator.config.profiles import PROFILES, ProfileConfig
    from data_generator.injectors import inject_all
    from data_generator.orchestrator import generate_all

    from bom_guardian.entity_resolution import ConfidenceBand, WeightedMatcher
    from bom_guardian.entity_resolution.evaluate import evaluate_matches
    from bom_guardian.entity_resolution.ml import (
        MLMatcherTrainer,
        build_pair_dataset,
        evaluate_across_seeds,
    )

    PROFILES["er_eval"] = ProfileConfig(
        name="er_eval",
        n_parts=args.n_parts,
        n_suppliers=max(30, args.n_parts // 30),
        n_plants=4,
        warehouses_per_plant=2,
    )
    clean = generate_all("er_eval", args.seed)
    injected = inject_all(clean, seed=args.seed, rate=args.rate)
    parts, gt = injected.data["part_master"], injected.ground_truth

    # unsupervised baseline over all labeled pairs (no split needed)
    matches = WeightedMatcher().find_matches(parts)
    baseline = {
        "recommend_band": evaluate_matches(matches, gt, ConfidenceBand.RECOMMEND),
        "review_band": evaluate_matches(matches, gt, ConfidenceBand.REVIEW),
    }

    dataset = build_pair_dataset(parts, gt)
    aggregated = evaluate_across_seeds(dataset, seeds=SPLIT_SEEDS)
    # a single representative run for the persisted models + coefficients
    trainer = MLMatcherTrainer(seed=args.seed)
    single_run = trainer.train_and_evaluate(dataset)
    artifacts = REPO / "models" / "artifacts"
    for name in ("logistic_regression", "gradient_boosting"):
        trainer.save(name, artifacts / f"er_{name}.joblib")

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "profile": "er_eval",
        "n_parts": args.n_parts,
        "inject_rate": args.rate,
        "data_seed": args.seed,
        "split_seeds": SPLIT_SEEDS,
        "methodology": (
            "Candidate pairs from blocking are labeled from injected ground truth. "
            "Folds are entity-disjoint (connected-component grouping over the "
            "candidate-pair graph; part-set disjointness asserted). The dataset is "
            "fixed; only the 60/20/20 split varies across split_seeds, giving the "
            "mean ± std bands below. Baseline is unsupervised over all labeled pairs."
        ),
        "labeled_duplicate_pairs": dataset.n_truth_pairs,
        "candidate_generation_recall": dataset.candidate_generation_recall,
        "weighted_baseline": baseline,
        "ml_aggregated": aggregated,
        "ml_single_run_for_persisted_models": {
            "seed": args.seed,
            "split": single_run["split"],
            "models": {
                k: {
                    m: v[m]
                    for m in (
                        "precision",
                        "recall",
                        "f1",
                        "threshold",
                        "test_positives",
                        "confusion_matrix",
                    )
                }
                for k, v in single_run["models"].items()
            },
            "lr_coefficients": single_run["models"]["logistic_regression"]["coefficients"],
        },
    }
    out = REPO / "evaluation" / "entity_resolution" / "ml_eval.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    print(f"Report written to {out}")
    print(f"labeled duplicate pairs: {dataset.n_truth_pairs}")
    print(f"candidate-generation recall: {dataset.candidate_generation_recall}")
    for model, band in aggregated["aggregated"].items():
        print(
            f"{model}: P {band['precision']['mean']}±{band['precision']['std']} "
            f"R {band['recall']['mean']}±{band['recall']['std']} "
            f"F1 {band['f1']['mean']}±{band['f1']['std']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
