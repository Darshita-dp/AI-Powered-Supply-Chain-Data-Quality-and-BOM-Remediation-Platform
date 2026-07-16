"""Detection-recall evaluation: which injected defects did the rule engine flag?

Usage:
    python scripts/evaluate_detection.py [--profile smoke] [--seed 20260716]

Writes evaluation/data_quality/detection_<profile>.json. This measures RECALL per
injected issue type against ground truth. Precision is not reported here because
the synthetic baseline also contains organic (non-injected) defects by design, so
issues without labels are not automatically false positives; see the note in the
report payload.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

# injected issue type -> rule ids expected to flag the affected record id
TYPE_TO_RULES: dict[str, list[str]] = {
    "invalid_uom": ["VALD-001"],
    "zero_component_quantity": ["VALD-006"],
    "negative_component_quantity": ["VALD-007"],
    "orphan_bom_component": ["REFI-002"],
    "orphan_bom_parent": ["REFI-001"],
    "self_referencing_bom": ["GRPH-001"],
    "blocked_part_with_future_demand": ["XFLD-003"],
    "invalid_plant_relationship": ["REFI-004"],
    "invalid_supplier_relationship": ["REFI-003"],
    "stale_record": ["TEMP-002"],
    "exact_duplicate_part": ["UNIQ-001", "UNIQ-002", "UNIQ-004"],
    "currency_inconsistency": ["VALD-002", "XFLD-006"],
    "extreme_cost_change": ["ANOM-001"],
    "extreme_lead_time_change": ["ANOM-002"],
    "supplier_doc_vs_erp_discrepancy": ["DOCR-001"],
    "multiple_active_revisions": ["UNIQ-005"],
    "overlapping_effective_dates": ["TEMP-001"],
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="smoke")
    parser.add_argument("--seed", type=int, default=20260716)
    args = parser.parse_args()

    from data_generator.orchestrator import DEFAULT_OUTPUT_ROOT, run_generation

    from bom_guardian.ingestion import IngestionService
    from bom_guardian.quality import RuleEngine
    from bom_guardian.testing import TRANSFORM_SQL
    from bom_guardian.warehouse import LocalWarehouse

    started = time.perf_counter()
    run_generation(args.profile, args.seed, inject=True)
    out_dir = DEFAULT_OUTPUT_ROOT / args.profile
    wh = LocalWarehouse(":memory:")
    svc = IngestionService(wh)
    svc.ingest_directory(out_dir, profile=args.profile)
    svc.load_ground_truth(out_dir / "ground_truth" / "labels.csv")
    for sql in TRANSFORM_SQL:
        wh.execute(sql)
    summary = RuleEngine(wh).run_all()

    detected = wh.query("SELECT DISTINCT rule_id, entity_key FROM quality.dq_issues")
    by_rule: dict[str, set[str]] = {}
    for _, row in detected.iterrows():
        by_rule.setdefault(row["rule_id"], set()).add(str(row["entity_key"]))

    gt = wh.query("SELECT issue_type, record_id FROM ground_truth.labels")
    per_type: dict[str, dict] = {}
    total_labeled = total_found = 0
    for issue_type, rules in TYPE_TO_RULES.items():
        labels = gt[gt["issue_type"] == issue_type]["record_id"].astype(str)
        if labels.empty:
            continue
        flagged = set().union(*(by_rule.get(r, set()) for r in rules))
        found = int(labels.isin(flagged).sum())
        per_type[issue_type] = {
            "labeled": len(labels),
            "detected": found,
            "recall": round(found / len(labels), 4),
            "rules": rules,
        }
        total_labeled += len(labels)
        total_found += found

    unmapped = sorted(set(gt["issue_type"].unique()) - set(TYPE_TO_RULES))
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "profile": args.profile,
        "seed": args.seed,
        "note": (
            "Recall vs injected ground truth. Precision is not computed because the "
            "clean baseline also contains organic defects; unlabeled issues are not "
            "necessarily false positives. Issue types requiring entity resolution or "
            "detected by evidence-only comparison are listed under unmapped_types."
        ),
        "rules_executed": summary["rules_executed"],
        "issues_created": summary["issues_created"],
        "overall_recall_on_mapped_types": round(total_found / total_labeled, 4)
        if total_labeled
        else None,
        "labeled_defects_mapped": total_labeled,
        "detected_defects_mapped": total_found,
        "per_type": per_type,
        "unmapped_types": unmapped,
        "duration_seconds": round(time.perf_counter() - started, 1),
    }
    out = REPO / "evaluation" / "data_quality" / f"detection_{args.profile}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    wh.close()
    print(f"Report written to {out}")
    print(
        f"overall recall (mapped types): {payload['overall_recall_on_mapped_types']} "
        f"({total_found}/{total_labeled})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
