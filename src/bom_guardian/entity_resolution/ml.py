"""ML entity resolution: logistic regression and gradient boosting over the
same interpretable features as the weighted baseline.

Labeling: blocked candidate pairs are labeled positive when they appear in the
injected ground truth (duplicate -> its original). Splits are group-aware — all
pairs touching one ground-truth entity stay in the same fold — to prevent
leakage. Threshold selection maximizes F1 subject to a precision floor because
wrong merges are operationally damaging.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
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
    groups: np.ndarray  # group id per pair (min part id) for leakage-safe splits
    pairs: list[tuple[str, str]]
    difficulty: list[str | None]


def build_pair_dataset(parts: pd.DataFrame, ground_truth: pd.DataFrame) -> PairDataset:
    truth = _truth_pairs(ground_truth)
    by_id = parts.set_index("part_id", drop=False)
    pairs = sorted(generate_candidate_pairs(parts))
    rows, labels, groups, difficulty = [], [], [], []
    for a, b in pairs:
        feats = pair_features(by_id.loc[a], by_id.loc[b])
        rows.append([feats[name] for name in FEATURE_NAMES])
        labels.append(1 if (a, b) in truth else 0)
        groups.append(a)  # ties every pair for entity `a` into one fold
        difficulty.append(truth.get((a, b)))
    return PairDataset(
        X=np.array(rows),
        y=np.array(labels),
        groups=np.array(groups),
        pairs=pairs,
        difficulty=difficulty,
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

    def train_and_evaluate(self, dataset: PairDataset) -> dict:
        """Group-aware 60/20/20 split; returns full comparison report."""
        gss = GroupShuffleSplit(n_splits=1, test_size=0.4, random_state=self.seed)
        train_idx, rest_idx = next(gss.split(dataset.X, dataset.y, dataset.groups))
        gss2 = GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=self.seed)
        val_rel, test_rel = next(
            gss2.split(dataset.X[rest_idx], dataset.y[rest_idx], dataset.groups[rest_idx])
        )
        val_idx, test_idx = rest_idx[val_rel], rest_idx[test_rel]

        models = {
            "logistic_regression": LogisticRegression(max_iter=2000, class_weight="balanced"),
            "gradient_boosting": GradientBoostingClassifier(random_state=self.seed),
        }
        report: dict = {
            "features": FEATURE_NAMES,
            "split": {
                "train_pairs": len(train_idx),
                "validation_pairs": len(val_idx),
                "test_pairs": len(test_idx),
                "positives_total": int(dataset.y.sum()),
                "group_aware": True,
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
