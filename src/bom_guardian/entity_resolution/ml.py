"""ML entity resolution: logistic regression and gradient boosting over the
same interpretable features as the weighted baseline.

Labeling: blocked candidate pairs are labeled positive when they appear in the
injected ground truth (duplicate -> its original).

Leakage control: candidate pairs form a graph over part ids; its connected
components become split groups, and folds split by component. Because any two
parts that are ever compared share a component, no real-world entity — and no
candidate pair — can span more than one train/val/test fold. Part-set
disjointness of the three folds is asserted at runtime. Evaluation is repeated
across several split seeds (see evaluate_across_seeds) so metrics carry a
dispersion band rather than a single fragile point estimate. Threshold selection
maximizes F1 subject to a precision floor because wrong merges are operationally
damaging.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, precision_recall_curve
from sklearn.model_selection import GroupShuffleSplit

from bom_guardian.entity_resolution.blocking import generate_candidate_pairs
from bom_guardian.entity_resolution.evaluate import _truth_pairs
from bom_guardian.entity_resolution.features import FEATURE_NAMES, pair_features
from bom_guardian.observability import get_logger

PRECISION_FLOOR = 0.95


@dataclass
class PairDataset:
    X: np.ndarray
    y: np.ndarray
    # group id per pair = connected-component id over the candidate-pair graph.
    # Two parts that are ever compared land in the same component, so no real-world
    # entity — and no candidate pair — can span more than one train/val/test fold.
    groups: np.ndarray
    parts_a: np.ndarray  # part id of each pair's first endpoint (for disjointness checks)
    parts_b: np.ndarray
    pairs: list[tuple[str, str]]
    difficulty: list[str | None]
    # candidate-generation diagnostics (independent of any model)
    n_truth_pairs: int  # labeled duplicate pairs in ground truth
    n_truth_pairs_as_candidates: int  # of those, how many blocking actually produced

    @property
    def candidate_generation_recall(self) -> float:
        return (
            round(self.n_truth_pairs_as_candidates / self.n_truth_pairs, 4)
            if self.n_truth_pairs
            else 0.0
        )


def _connected_component_groups(pairs: list[tuple[str, str]]) -> dict[str, int]:
    """Map every part id in the candidate-pair graph to a stable component id.

    Nodes are part ids, edges are candidate pairs. Components are numbered by their
    smallest member so the mapping is deterministic across runs.
    """
    g = nx.Graph()
    g.add_edges_from(pairs)
    components = sorted((sorted(c) for c in nx.connected_components(g)), key=lambda c: c[0])
    return {node: cid for cid, comp in enumerate(components) for node in comp}


def build_pair_dataset(parts: pd.DataFrame, ground_truth: pd.DataFrame) -> PairDataset:
    truth = _truth_pairs(ground_truth)
    by_id = parts.set_index("part_id", drop=False)
    pairs = sorted(generate_candidate_pairs(parts))
    component_of = _connected_component_groups(pairs)

    rows, labels, groups, difficulty = [], [], [], []
    parts_a, parts_b = [], []
    for a, b in pairs:
        feats = pair_features(by_id.loc[a], by_id.loc[b])
        rows.append([feats[name] for name in FEATURE_NAMES])
        labels.append(1 if (a, b) in truth else 0)
        # a and b are edge-connected, so they share a component id — pick either
        groups.append(component_of[a])
        parts_a.append(a)
        parts_b.append(b)
        difficulty.append(truth.get((a, b)))

    candidate_set = set(pairs)
    n_truth_as_cand = sum(1 for p in truth if p in candidate_set)
    return PairDataset(
        X=np.array(rows),
        y=np.array(labels),
        groups=np.array(groups),
        parts_a=np.array(parts_a),
        parts_b=np.array(parts_b),
        pairs=pairs,
        difficulty=difficulty,
        n_truth_pairs=len(truth),
        n_truth_pairs_as_candidates=n_truth_as_cand,
    )


def _select_threshold(y_true: np.ndarray, scores: np.ndarray) -> float:
    """Best-F1 threshold subject to the precision floor (fallback: max precision)."""
    precision, recall, thresholds = precision_recall_curve(y_true, scores)
    best_t, best_f1 = 0.5, -1.0
    for p, r, t in zip(precision[:-1], recall[:-1], thresholds, strict=True):
        if p >= PRECISION_FLOOR and p + r > 0:
            f1 = 2 * p * r / (p + r)
            if f1 > best_f1:
                best_f1, best_t = f1, float(t)
    if best_f1 < 0:  # floor unreachable; pick threshold with max precision
        best_t = float(thresholds[int(np.argmax(precision[:-1]))]) if len(thresholds) else 0.5
    return best_t


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(2 * precision * recall / (precision + recall), 4)
        if precision + recall
        else 0.0,
        "false_positive_rate": round(float(fp / (fp + tn)) if fp + tn else 0.0, 6),
        "false_negative_rate": round(float(fn / (fn + tp)) if fn + tp else 0.0, 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


class MLMatcherTrainer:
    """Trains and evaluates LR + gradient-boosting duplicate classifiers."""

    def __init__(self, seed: int = 20260716) -> None:
        self.seed = seed
        self._log = get_logger("ml_matcher")

    def _split_indices(self, dataset: PairDataset) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Entity-disjoint 60/20/20 split by connected-component group.

        Asserts the part-id sets of the three folds are pairwise disjoint, so no
        real-world entity (and no candidate pair) can leak across the split.
        """
        gss = GroupShuffleSplit(n_splits=1, test_size=0.4, random_state=self.seed)
        train_idx, rest_idx = next(gss.split(dataset.X, dataset.y, dataset.groups))
        gss2 = GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=self.seed)
        val_rel, test_rel = next(
            gss2.split(dataset.X[rest_idx], dataset.y[rest_idx], dataset.groups[rest_idx])
        )
        val_idx, test_idx = rest_idx[val_rel], rest_idx[test_rel]
        self._assert_entity_disjoint(dataset, train_idx, val_idx, test_idx)
        return train_idx, val_idx, test_idx

    @staticmethod
    def _parts_in(dataset: PairDataset, idx: np.ndarray) -> set[str]:
        return set(dataset.parts_a[idx]) | set(dataset.parts_b[idx])

    def _assert_entity_disjoint(
        self,
        dataset: PairDataset,
        train_idx: np.ndarray,
        val_idx: np.ndarray,
        test_idx: np.ndarray,
    ) -> None:
        tr, va, te = (self._parts_in(dataset, i) for i in (train_idx, val_idx, test_idx))
        overlaps = {
            "train∩val": tr & va,
            "train∩test": tr & te,
            "val∩test": va & te,
        }
        leaked = {k: sorted(v)[:5] for k, v in overlaps.items() if v}
        if leaked:
            raise AssertionError(f"entity leakage across folds: {leaked}")

    def _split_composition(self, dataset: PairDataset, idx: np.ndarray) -> dict:
        y = dataset.y[idx]
        parts = self._parts_in(dataset, idx)
        return {
            "pairs": len(idx),
            "positive_pairs": int(y.sum()),
            "negative_pairs": int((y == 0).sum()),
            "unique_parts": len(parts),
            "unique_components": len(set(dataset.groups[idx])),
        }

    def train_and_evaluate(self, dataset: PairDataset) -> dict:
        """Entity-disjoint 60/20/20 evaluation; returns full comparison report."""
        train_idx, val_idx, test_idx = self._split_indices(dataset)

        models = {
            "logistic_regression": LogisticRegression(max_iter=2000, class_weight="balanced"),
            "gradient_boosting": GradientBoostingClassifier(random_state=self.seed),
        }
        report: dict = {
            "features": FEATURE_NAMES,
            "seed": self.seed,
            "split": {
                "strategy": "connected_component_entity_disjoint",
                "entity_disjoint_asserted": True,
                "train": self._split_composition(dataset, train_idx),
                "validation": self._split_composition(dataset, val_idx),
                "test": self._split_composition(dataset, test_idx),
            },
            "candidate_generation": {
                "labeled_duplicate_pairs": dataset.n_truth_pairs,
                "produced_as_candidates": dataset.n_truth_pairs_as_candidates,
                "candidate_generation_recall": dataset.candidate_generation_recall,
                "note": (
                    "Model recall below is conditional on candidate generation: it can "
                    "only recover duplicate pairs that blocking produced. End-to-end "
                    "recall = candidate_generation_recall * model_recall_on_candidates."
                ),
            },
            "precision_floor": PRECISION_FLOOR,
            "models": {},
        }
        self._trained: dict[str, tuple] = {}
        for name, model in models.items():
            model.fit(dataset.X[train_idx], dataset.y[train_idx])
            val_scores = model.predict_proba(dataset.X[val_idx])[:, 1]
            threshold = _select_threshold(dataset.y[val_idx], val_scores)
            test_scores = model.predict_proba(dataset.X[test_idx])[:, 1]
            y_pred = (test_scores >= threshold).astype(int)
            m = _metrics(dataset.y[test_idx], y_pred)
            m["threshold"] = round(threshold, 4)
            m["test_positives"] = int(dataset.y[test_idx].sum())
            m["recall_note"] = "model recall on candidate pairs in the held-out test fold"
            m["recall_by_difficulty"] = self._recall_by_difficulty(dataset, test_idx, y_pred)
            if name == "logistic_regression":
                m["coefficients"] = {
                    f: round(float(c), 4)
                    for f, c in zip(FEATURE_NAMES, model.coef_[0], strict=True)
                }
            report["models"][name] = m
            self._trained[name] = (model, threshold)
            self._log.info("model_evaluated", model=name, **m["confusion_matrix"])
        return report

    @staticmethod
    def _recall_by_difficulty(
        dataset: PairDataset, test_idx: np.ndarray, y_pred: np.ndarray
    ) -> dict:
        out: dict[str, dict] = {}
        for diff in ("easy", "medium", "hard"):
            mask = np.array([dataset.difficulty[i] == diff and dataset.y[i] == 1 for i in test_idx])
            if not mask.any():
                continue
            found = int(y_pred[mask].sum())
            out[diff] = {
                "labeled": int(mask.sum()),
                "found": found,
                "recall": round(found / int(mask.sum()), 4),
            }
        return out

    def save(self, model_name: str, path: Path) -> Path:
        model, threshold = self._trained[model_name]
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {"model": model, "threshold": threshold, "features": FEATURE_NAMES, "seed": self.seed},
            path,
        )
        return path

    @staticmethod
    def load(path: Path) -> dict:
        return joblib.load(path)


def evaluate_across_seeds(dataset: PairDataset, seeds: list[int]) -> dict:
    """Repeat the entity-disjoint evaluation under several split seeds and aggregate.

    The dataset (candidate pairs + features) is fixed; only the split varies, so this
    isolates split-variance. Reports mean ± std (a simple dispersion band) per model.
    """
    per_seed: list[dict] = []
    for seed in seeds:
        report = MLMatcherTrainer(seed=seed).train_and_evaluate(dataset)
        per_seed.append(report)

    def agg(model: str, metric: str) -> dict:
        vals = [float(r["models"][model][metric]) for r in per_seed]
        arr = np.array(vals)
        return {
            "mean": round(float(arr.mean()), 4),
            "std": round(float(arr.std(ddof=1)) if len(arr) > 1 else 0.0, 4),
            "min": round(float(arr.min()), 4),
            "max": round(float(arr.max()), 4),
            "values": [round(v, 4) for v in vals],
        }

    models = list(per_seed[0]["models"].keys())
    return {
        "seeds": seeds,
        "n_runs": len(seeds),
        "split_strategy": "connected_component_entity_disjoint",
        "candidate_generation": per_seed[0]["candidate_generation"],
        "aggregated": {
            model: {
                metric: agg(model, metric)
                for metric in ("precision", "recall", "f1", "false_positive_rate")
            }
            for model in models
        },
        "per_seed_test_positives": [r["models"][models[0]]["test_positives"] for r in per_seed],
    }
