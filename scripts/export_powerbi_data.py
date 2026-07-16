"""Export marts + dims from the local warehouse to CSV for the Power BI fallback.

Usage:
    python scripts/export_powerbi_data.py

Writes powerbi/data/*.csv (git-ignored) from warehouse/local/bom_guardian.duckdb.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

TABLES = {
    "ExecutiveQuality": "marts.mart_executive_quality",
    "PartQuality": "marts.mart_part_quality",
    "BomIntegrity": "marts.mart_bom_integrity",
    "SupplierQuality": "marts.mart_supplier_quality",
    "BusinessImpact": "marts.mart_business_impact",
    "RemediationPerformance": "marts.mart_remediation_performance",
    "AIGovernance": "marts.mart_ai_governance",
    "DimPart": "core.dim_part",
    "DimSupplier": "core.dim_supplier",
    "DimPlant": "core.dim_plant",
    "DimDate": "core.dim_date",
}


def main() -> int:
    from bom_guardian.warehouse import LocalWarehouse

    db = REPO / "warehouse" / "local" / "bom_guardian.duckdb"
    if not db.exists():
        print("Warehouse missing — run scripts/run_local_pipeline.py first.")
        return 1
    out_dir = REPO / "powerbi" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    with LocalWarehouse(db) as wh:
        for name, table in TABLES.items():
            df = wh.query(f"SELECT * FROM {table}")
            path = out_dir / f"{name}.csv"
            df.to_csv(path, index=False)
            print(f"{name}: {len(df):,} rows -> {path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
