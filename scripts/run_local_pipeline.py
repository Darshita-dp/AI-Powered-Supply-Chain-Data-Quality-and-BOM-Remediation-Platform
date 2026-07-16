"""Run the local pipeline: generate -> inject -> ingest -> dbt build.

Usage:
    python scripts/run_local_pipeline.py [--profile smoke] [--seed 20260716]

Produces warehouse/local/bom_guardian.duckdb ready for dbt / quality runs.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="smoke")
    parser.add_argument("--seed", type=int, default=20260716)
    parser.add_argument("--skip-dbt", action="store_true")
    args = parser.parse_args()

    from data_generator.orchestrator import DEFAULT_OUTPUT_ROOT, run_generation

    from bom_guardian.ingestion import IngestionService
    from bom_guardian.warehouse import LocalWarehouse

    print(f"[1/3] Generating {args.profile} data with injection ...")
    run_generation(args.profile, args.seed, inject=True)
    out_dir = DEFAULT_OUTPUT_ROOT / args.profile

    db_path = REPO / "warehouse" / "local" / "bom_guardian.duckdb"
    print(f"[2/3] Ingesting into {db_path} ...")
    with LocalWarehouse(db_path) as wh:
        svc = IngestionService(wh)
        stats = svc.ingest_directory(out_dir, profile=args.profile)
        svc.load_ground_truth(out_dir / "ground_truth" / "labels.csv")
    print(f"    batch={stats['batch_id']} rows={stats['rows_loaded']:,}")

    if args.skip_dbt:
        return 0

    print("[3/5] Running dbt build for staging + core (local DuckDB target) ...")
    dbt = [sys.executable, "-m", "dbt.cli.main"]
    common = ["--profiles-dir", ".", "--project-dir", "."]
    result = subprocess.run(
        [*dbt, "build", "--exclude", "marts", *common], cwd=REPO / "dbt_supply_chain"
    )
    if result.returncode != 0:
        return result.returncode

    print("[4/5] Running data-quality rules and scoring ...")
    from api.app.services import IssueService

    from bom_guardian.ai import DeterministicMockAIProvider, RemediationEngine
    from bom_guardian.quality import QualityScorer, RuleEngine

    with LocalWarehouse(db_path) as wh:
        summary = RuleEngine(wh).run_all()
        scores = QualityScorer(wh).run_all()
        # instantiate services so their audit tables exist for the marts layer
        RemediationEngine(DeterministicMockAIProvider(), warehouse=wh)
        IssueService(wh)
    print(
        f"    rules={summary['rules_executed']} failed={summary['rules_failed']} "
        f"issues={summary['issues_created']:,} "
        f"enterprise_score={scores['enterprise_quality_score']}"
    )

    print("[5/5] Building analytics marts ...")
    result = subprocess.run(
        [*dbt, "build", "--select", "marts", *common], cwd=REPO / "dbt_supply_chain"
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
