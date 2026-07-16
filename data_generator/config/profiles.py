"""Data-profile scaling. Totals are emergent, never hard-coded in docs:
the generation manifest reports actual counts per run.

Rough targets (emergent totals depend on ratios):
- smoke: ~10k-25k records total, for fast tests
- demo:  ~200k-400k records, for application demos
- full:  ~1.5M-2.5M records, for performance evaluation
"""

from __future__ import annotations

from pydantic import BaseModel


class ProfileConfig(BaseModel):
    name: str
    n_parts: int
    n_suppliers: int
    n_plants: int
    warehouses_per_plant: int
    # Ratios / multipliers applied to n_parts unless stated
    alias_ratio: float = 0.15  # share of parts with at least one alias
    assembly_ratio: float = 0.18  # share of parts that are assemblies (BOM parents)
    avg_components_per_bom: int = 6
    revisions_per_assembly: float = 1.6
    eco_ratio: float = 0.08
    substitution_ratio: float = 0.04
    supersession_ratio: float = 0.03
    suppliers_per_part: float = 1.4  # supplier-part relationships per purchased part
    inventory_snapshots: int = 2  # snapshot dates
    po_lines_per_part: float = 1.5
    demand_rows_per_part: float = 1.2
    production_order_ratio: float = 0.25  # per assembly
    cost_history_per_part: int = 3
    lead_time_history_per_part: int = 2
    quote_ratio: float = 0.30


PROFILES: dict[str, ProfileConfig] = {
    "smoke": ProfileConfig(
        name="smoke", n_parts=900, n_suppliers=60, n_plants=3, warehouses_per_plant=2
    ),
    "demo": ProfileConfig(
        name="demo", n_parts=16000, n_suppliers=500, n_plants=6, warehouses_per_plant=2
    ),
    "full": ProfileConfig(
        name="full", n_parts=110000, n_suppliers=2500, n_plants=10, warehouses_per_plant=3
    ),
}
