# Model Card — Duplicate Part Entity Resolution

## Overview

| | |
|---|---|
| Task | Pairwise duplicate-part classification (match / non-match) |
| Models | Weighted deterministic baseline, logistic regression, gradient boosting (scikit-learn) |
| Features | 11 interpretable pair-similarity features (`src/bom_guardian/entity_resolution/features.py`) |
| Training data | Blocked candidate pairs from synthetic parts with injected duplicates; positives labeled from injected ground truth |
| Splits | Group-aware 60/20/20 (GroupShuffleSplit keyed on entity) — no entity appears in more than one fold |
| Threshold policy | Selected on validation: max F1 subject to **precision ≥ 0.95** (wrong merges are operationally damaging) |
| Persistence | joblib bundles (model + threshold + feature list + seed) in `models/artifacts/` (git-ignored) |
| Reproduce | `python scripts/train_entity_resolution.py --profile smoke` |

## Measured results (smoke profile, seed 20260716)

Source: `evaluation/entity_resolution/ml_smoke.json` — generated, not hand-written.

| Model | Precision | Recall | F1 | Scope |
|---|---|---|---|---|
| Weighted baseline (recommend band) | 1.00 | 0.57 | 0.73 | all labeled pairs |
| Weighted baseline (review band) | 1.00 | 0.86 | 0.92 | all labeled pairs |
| Logistic regression | 1.00 | 0.83 | 0.91 | held-out test split |
| Gradient boosting | 1.00 | 1.00 | 1.00 | held-out test split |

**Caveats on these numbers (read before quoting):**

- The smoke profile yields a small positive class (~30 labeled duplicate pairs; the
  held-out test split contains only ~6 positives), so recall estimates have wide
  uncertainty. Larger-profile evaluation is scheduled for M20.
- Baseline metrics are computed over *all* labeled pairs; ML metrics are on the
  held-out test split. Method is comparable; denominators are not identical.
- Duplicates are synthetic perturbations (casing, abbreviation, typos, transposition).
  Real ERP duplicates include failure modes not modeled here (multilingual
  descriptions, semantic synonyms, unit conversions).

## Intended use and limits

- **Use:** ranking duplicate-part candidates for human steward review inside BOM
  Guardian AI. Output feeds recommend/review/abstain bands; **nothing auto-merges.**
- **Do not use** for autonomous master-data consolidation, or on real ERP data without
  re-training and re-evaluation on representative labeled pairs.

## Explainability

- All features are human-readable similarities; each candidate carries per-feature
  evidence shown in the UI.
- Logistic-regression coefficients are exported in the evaluation report.
- The gradient-boosting model is less directly interpretable; it is gated by the same
  evidence display and human-approval workflow.

## Ethics and data

All data is synthetic; no real supplier, part, or personal data was used. Ground-truth
labels are isolated from model inputs (ADR-004) and used only for supervision/evaluation
of injected defects.
