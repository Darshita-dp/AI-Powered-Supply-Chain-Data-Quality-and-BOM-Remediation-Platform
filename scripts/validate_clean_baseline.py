"""Clean-baseline validation for the data-quality evaluation (hardening H3).

Runs the full rule engine on the generated data BEFORE any defect injection and
reports which rules fire organically. The generator aims for a clean baseline, but
some conditions are intentional realism (e.g. a fraction of parts deliberately lack
a manufacturer part number). Those are the documented allowlist; any rule NOT on the
allowlist must report zero organic violations or the baseline is not clean.

Usage:
    python scripts/validate_clean_baseline.py [--profile smoke] [--seed 20260716]

Writes evaluation/data_quality/clean_baseline_<profile>.json.
Exit code 1 if a non-allowlisted rule fires on the clean baseline.
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

# Rules that legitimately fire on the clean baseline because the corresponding
# condition is intentional synthetic realism (not a defect to remediate).
# Each entry documents WHY it is expected.
BASELINE_ALLOWLIST: dict[str, str] = {
    "COMP-008": "≈25% of parts intentionally have no manufacturer part number (realistic).",
    "XFLD-001": "Some MAKE parts at tier>=2 legitimately have no BOM yet (in-development items).",
    "TEMP-002": "A share of active parts are intentionally older than the staleness threshold.",
    "ANOM-001": "Cost history walks with random drift; a few steps naturally exceed the 4x band.",
    "ANOM-002": "Lead-time history drifts; a few steps naturally exceed the 3x band.",
    "ANOM-004": "Multi-supplier parts naturally show price spread; a few exceed the 2.5x band.",
    "DOCR-001": "Quotes are generated with +/-10% price noise vs ERP; some exceed the 30% band.",
    "DOCR-002": "Quotes carry lead-time noise vs ERP; some exceed the 14-day band.",
    "DOCR-003": "Some quotes are generated already past their validity window.",
    "GRPH-003": "Shared components can legitimately appear under one parent across revisions.",
}


def _run_rules_on_clean(profile: str, seed: int):  # type: ignore[no-untyped-def]
    from data_generator.orchestrator import DEFAULT_OUTPUT_ROOT, run_generation

    from bom_guardian.ingestion import IngestionService
    from bom_guardian.quality import RuleEngine
    from bom_guardian.testing import TRANSFORM_SQL
    from bom_guardian.warehouse import LocalWarehouse

    # inject=False → the clean baseline
    run_generation(profile, seed, inject=False)
    out_dir = DEFAULT_OUTPUT_ROOT / profile
    wh = LocalWarehouse(":memory:")
    svc = IngestionService(wh)
    svc.ingest_directory(out_dir, profile=profile)
    for sql in TRANSFORM_SQL:
        wh.execute(sql)
    summary = RuleEngine(wh).run_all()
    counts = wh.query(
        "SELECT rule_id, COUNT(*) AS n FROM quality.dq_issues GROUP BY 1 ORDER BY n DESC"
    )
    wh.close()
    return summary, {r["rule_id"]: int(r["n"]) for r in counts.to_dict("records")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="smoke")
    parser.add_argument("--seed", type=int, default=20260716)
    args = parser.parse_args()

    summary, organic = _run_rules_on_clean(args.profile, args.seed)
    unexpected = {rid: n for rid, n in organic.items() if rid not in BASELINE_ALLOWLIST}
    clean = len(unexpected) == 0

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "profile": args.profile,
        "seed": args.seed,
        "rules_executed": summary["rules_executed"],
        "clean_baseline": clean,
        "note": (
            "A baseline is 'clean' when the only rules that fire are on the documented "
            "allowlist of intentional realism. Precision in detection_<profile>.json is "
            "computed by diffing injected-run issues against these organic baseline "
            "issues, so allowlisted organic hits are never counted as false positives."
        ),
        "organic_violations": organic,
        "allowlist": BASELINE_ALLOWLIST,
        "unexpected_violations": unexpected,
    }
    out = REPO / "evaluation" / "data_quality" / f"clean_baseline_{args.profile}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    print(f"Report written to {out}")
    print(f"clean_baseline={clean}")
    if not clean:
        print("UNEXPECTED (non-allowlisted) organic violations:")
        for rid, n in sorted(unexpected.items(), key=lambda kv: -kv[1]):
            print(f"  {rid}: {n}")
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
