"""Deploy the BOM Guardian schema to Snowflake and load a data profile.

Status: implemented locally; external Snowflake execution pending. With no credentials
this runs in --dry-run mode (the default): it validates that every provisioning script
exists, prints the ordered execution plan, and exits without connecting. With
--execute and SNOWFLAKE_* env vars set, it runs the provisioning scripts, loads the
generated CSVs into RAW via the SnowflakeWarehouse adapter, and validates the layout.

Usage:
    python scripts/deploy_snowflake.py                      # dry run (plan only)
    python scripts/deploy_snowflake.py --execute --profile smoke   # requires credentials
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

SNOW = REPO / "warehouse" / "snowflake"
PROVISION_ORDER = [
    SNOW / "setup" / "01_database_and_schemas.sql",
    SNOW / "setup" / "02_warehouses.sql",
    SNOW / "security" / "01_roles_and_grants.sql",
    SNOW / "ingestion" / "01_stages_and_formats.sql",
]


def _split_statements(sql: str) -> list[str]:
    return [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Actually run against Snowflake")
    parser.add_argument("--profile", default="smoke")
    parser.add_argument("--seed", type=int, default=20260716)
    args = parser.parse_args()

    missing = [p for p in PROVISION_ORDER if not p.exists()]
    if missing:
        print("MISSING provisioning scripts:", [str(p) for p in missing])
        return 1

    print("Provisioning plan (in order):")
    for p in PROVISION_ORDER:
        n = len(_split_statements(p.read_text()))
        print(f"  - {p.relative_to(REPO)}  ({n} statements)")
    print("Then: load generated RAW CSVs via SnowflakeWarehouse.load_dataframe(), then validate().")
    print("Teardown: warehouse/snowflake/teardown/01_teardown.sql")

    if not args.execute:
        print(
            "\nDRY RUN (default). No connection attempted. Re-run with --execute and the "
            "SNOWFLAKE_* environment variables set to deploy for real. Status: external "
            "Snowflake execution pending — this has never run against a live account."
        )
        return 0

    # --- real execution path (requires credentials) ---
    import os

    from data_generator.orchestrator import DEFAULT_OUTPUT_ROOT, run_generation

    from bom_guardian.ingestion import IngestionService
    from bom_guardian.warehouse.snowflake import SnowflakeWarehouse

    if not os.environ.get("SNOWFLAKE_ACCOUNT"):
        print("SNOWFLAKE_ACCOUNT is not set; cannot --execute. Aborting.")
        return 1

    wh = SnowflakeWarehouse()
    try:
        for p in PROVISION_ORDER:
            print(f"Running {p.name} ...")
            for stmt in _split_statements(p.read_text()):
                wh.execute(stmt)
        print(f"Generating + loading {args.profile} data ...")
        run_generation(args.profile, args.seed, inject=True)
        IngestionService(wh).ingest_directory(  # same auditable loader, Snowflake backend
            DEFAULT_OUTPUT_ROOT / args.profile, profile=args.profile
        )
        layout = wh.validate()
        print("Validated layout:", {k: len(v) for k, v in layout.items()})
    finally:
        wh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
