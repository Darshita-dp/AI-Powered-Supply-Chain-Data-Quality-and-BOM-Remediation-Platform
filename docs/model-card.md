# Model Card — Duplicate Part Entity Resolution

## Overview

| | |
|---|---|
| Task | Pairwise duplicate-part classification (match / non-match) |
| Models | Weighted deterministic baseline, logistic regression, gradient boosting (scikit-learn) |
| Features | 11 interpretable pair-similarity features (`src/bom_guardian/entity_resolution/features.py`) |
| Training data | Blocked candidate pairs from synthetic parts with injected duplicates; positives labeled from injected ground truth |
| Splits | **Entity-disjoint** 60/20/20: candidate pairs form a graph over part ids, connected components become groups, folds split by component. Part-set disjointness of train/val/test is asserted at runtime (`_assert_entity_disjoint`). |
| Robustness | Evaluated across 5 split seeds; results reported as mean ± std, not a single point |
| Threshold policy | Selected on validation: max F1 subject to **precision ≥ 0.95** (wrong merges are operationally damaging) |
| Persistence | joblib bundles (model + threshold + feature list + seed) in `models/artifacts/` (git-ignored) |
| Reproduce | `python scripts/train_entity_resolution.py` (4,000-part `er_eval` profile, rate 0.05) |

## Measured results — leakage-safe (hardening H2)

Source: `evaluation/entity_resolution/ml_eval.json` — generated, not hand-written.
Population: **409 labeled duplicate pairs**; **candidate-generation recall 0.95**
(blocking produces 95% of labeled duplicate pairs — the ceiling on end-to-end recall).

| Model | Precision | Recall | F1 | Scope |
|---|---|---|---|---|
| Weighted baseline (recommend band) | 0.97 | 0.57 | — | all labeled pairs (unsupervised) |
| Weighted baseline (review band) | 0.96 | 0.77 | — | all labeled pairs (unsupervised) |
| **Logistic regression** | **0.962 ± 0.010** | **0.804 ± 0.178** | **0.867 ± 0.113** | entity-disjoint test fold, 5 seeds |
| Gradient boosting | 0.769 ± 0.431 | 0.471 ± 0.375 | 0.547 ± 0.394 | entity-disjoint test fold, 5 seeds |

Model recall is **conditional on candidate generation**: end-to-end recall ≈
candidate-generation recall (0.95) × model recall on candidates.

### What changed vs. the earlier (retired) numbers

The previous card reported gradient boosting at P=1.00/R=1.00. That was an artifact of
(a) a split grouped on the first part ID only — not provably entity-disjoint — and
(b) a test fold with only ~6 positives. Under a genuinely entity-disjoint split over a
much larger labeled set:

- **Logistic regression is the stable, recommended model**: tight precision
  (0.962 ± 0.010) and the best mean F1.
- **Gradient boosting is high-variance here** (recall 0.471 ± 0.375; one seed collapsed
  to 0/0). It over/under-fits on the small per-fold positive counts and should not be
  the headline model at this data scale.
- The interpretable baseline and logistic regression are the trustworthy options; the
  platform uses them accordingly and keeps a human in the loop regardless.

**Caveats (read before quoting):**

- Per-fold test positives still range from ~20 to ~140 across seeds, hence the wide
  recall/F1 bands — the mean ± std *is* the honest summary; do not quote a single seed.
- Duplicates are synthetic perturbations (casing, abbreviation, typos, transposition).
  Real ERP duplicates include failure modes not modeled here (multilingual descriptions,
  semantic synonyms, unit conversions).

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
