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

    print("[3/3] Running dbt build (local DuckDB target) ...")
    cmd = [
        sys.executable,
        "-m",
        "dbt.cli.main",
        "build",
        "--profiles-dir",
        ".",
        "--project-dir",
        ".",
    ]
    result = subprocess.run(cmd, cwd=REPO / "dbt_supply_chain")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
