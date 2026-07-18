"""Test support: build a fully-populated in-memory warehouse without dbt.

Used by the data-quality, API, and (service-level) end-to-end test suites so they run
in seconds without spawning `dbt build`. The SQL views below deliberately mirror the
dbt staging/core models for the columns the engine consumes.

DRIFT RISK: these views duplicate production logic and could silently diverge from the
real dbt models. Two guards keep them honest:
  1. tests/end_to_end/test_dbt_pipeline.py invokes the REAL dbt project and fails if any
     model/mart breaks — so correctness of the actual pipeline is covered there.
  2. That same test asserts the dbt-built core.dim_part exposes the same columns these
     views produce (see _assert_no_fixture_drift), so a schema drift fails the suite.
If you change a dbt staging/core model's columns, update the matching view here too.
"""

from __future__ import annotations

from pathlib import Path

from data_generator.config.profiles import PROFILES, ProfileConfig
from data_generator.orchestrator import run_generation

from bom_guardian.ingestion import IngestionService
from bom_guardian.warehouse import LocalWarehouse

TRANSFORM_SQL: list[str] = [
    """
    CREATE OR REPLACE VIEW staging.stg_supplier_parts AS
    SELECT supplier_part_id, supplier_id, part_id, supplier_part_number,
           regexp_replace(upper(trim(supplier_part_number)), '[^A-Z0-9]', '', 'g')
               AS supplier_part_number_normalized,
           CAST(unit_price AS DECIMAL(18,4)) AS unit_price,
           upper(trim(currency)) AS currency,
           CAST(lead_time_days AS INTEGER) AS lead_time_days,
           CAST(min_order_qty AS INTEGER) AS min_order_qty,
           CAST(is_primary AS BOOLEAN) AS is_primary
    FROM raw.supplier_parts
    """,
    """
    CREATE OR REPLACE VIEW staging.stg_engineering_revisions AS
    SELECT revision_id, bom_header_id, part_id,
           upper(trim(revision_label)) AS revision_label,
           CAST(effective_from AS DATE) AS effective_from,
           CAST(effective_to AS DATE) AS effective_to,
           CAST(is_current AS BOOLEAN) AS is_current
    FROM raw.engineering_revisions
    """,
    """
    CREATE OR REPLACE VIEW core.dim_part AS
    SELECT part_id AS part_key, source_part_number,
           regexp_replace(upper(trim(source_part_number)), '[^A-Z0-9]', '', 'g')
               AS part_number_normalized,
           source_system, description,
           upper(trim(category)) AS category, upper(trim(uom)) AS uom,
           upper(trim(lifecycle_status)) AS lifecycle_status,
           upper(trim(procurement_type)) AS procurement_type,
           manufacturer_part_number,
           regexp_replace(upper(trim(manufacturer_part_number)), '[^A-Z0-9]', '', 'g')
               AS mpn_normalized,
           CAST(standard_cost AS DECIMAL(18,4)) AS standard_cost,
           upper(trim(currency)) AS currency,
           CAST(lead_time_days AS INTEGER) AS lead_time_days,
           upper(trim(primary_plant)) AS primary_plant,
           CAST(bom_tier AS INTEGER) AS bom_tier,
           CAST(created_date AS DATE) AS created_date,
           CAST(last_updated AS DATE) AS last_updated
    FROM raw.part_master
    """,
    """
    CREATE OR REPLACE VIEW core.dim_supplier AS
    SELECT supplier_id AS supplier_key, supplier_name,
           regexp_replace(trim(upper(supplier_name)), '\\s+', ' ', 'g')
               AS supplier_name_normalized,
           upper(trim(country)) AS country, upper(trim(currency)) AS currency,
           upper(trim(payment_terms)) AS payment_terms, source_system,
           upper(trim(status)) AS status, CAST(created_date AS DATE) AS created_date
    FROM raw.suppliers
    """,
    "CREATE OR REPLACE VIEW core.dim_plant AS "
    "SELECT plant_code AS plant_key, plant_name, country, region, currency FROM raw.plants",
    """
    CREATE OR REPLACE VIEW core.fact_bom_relationship AS
    SELECT bom_component_id AS bom_rel_key, bom_header_id,
           parent_part_id AS parent_part_key, child_part_id AS child_part_key,
           CAST(quantity_per AS DECIMAL(18,4)) AS quantity_per, uom, revision_label,
           CAST(effective_from AS DATE) AS effective_from,
           CAST(effective_to AS DATE) AS effective_to, position
    FROM raw.bom_components
    """,
    """
    CREATE OR REPLACE VIEW core.fact_future_demand AS
    SELECT demand_id AS demand_key, part_id AS part_key, plant_code AS plant_key,
           CAST(demand_date AS DATE) AS demand_date,
           CAST(demand_qty AS DECIMAL(18,2)) AS demand_qty, demand_type
    FROM raw.future_demand
    """,
    """
    CREATE OR REPLACE VIEW core.fact_inventory AS
    SELECT inventory_id AS inventory_key, part_id AS part_key,
           warehouse_code AS warehouse_key, CAST(snapshot_date AS DATE) AS snapshot_date,
           CAST(on_hand_qty AS DECIMAL(18,2)) AS on_hand_qty,
           CAST(on_hand_value AS DECIMAL(18,2)) AS on_hand_value,
           CAST(safety_stock_qty AS DECIMAL(18,2)) AS safety_stock_qty
    FROM raw.inventory_snapshots
    """,
    """
    CREATE OR REPLACE VIEW core.fact_purchase_order AS
    SELECT l.po_line_id AS po_line_key, l.po_id, l.line_number,
           l.part_id AS part_key, h.supplier_id AS supplier_key,
           upper(trim(h.plant_code)) AS plant_key,
           CAST(h.order_date AS DATE) AS order_date, upper(trim(h.currency)) AS currency,
           upper(trim(h.status)) AS status, CAST(l.order_qty AS DECIMAL(18,2)) AS order_qty,
           CAST(l.unit_price AS DECIMAL(18,4)) AS unit_price,
           CAST(l.line_value AS DECIMAL(18,2)) AS line_value,
           CAST(l.promised_date AS DATE) AS promised_date
    FROM raw.purchase_order_lines l
    LEFT JOIN raw.purchase_orders h ON l.po_id = h.po_id
    """,
    """
    CREATE OR REPLACE VIEW core.fact_standard_cost AS
    SELECT cost_history_id AS cost_key, part_id AS part_key, plant_code AS plant_key,
           CAST(standard_cost AS DECIMAL(18,4)) AS standard_cost, currency,
           CAST(effective_from AS DATE) AS effective_from
    FROM raw.standard_cost_history
    """,
    """
    CREATE OR REPLACE VIEW core.fact_lead_time AS
    SELECT lead_time_history_id AS lead_time_key, part_id AS part_key,
           supplier_id AS supplier_key, CAST(lead_time_days AS INTEGER) AS lead_time_days,
           CAST(effective_from AS DATE) AS effective_from
    FROM raw.lead_time_history
    """,
]


def build_test_warehouse(
    tmp_dir: Path,
    n_parts: int = 300,
    seed: int = 11,
    inject_rate: float = 0.03,
    profile_name: str = "tiny",
) -> LocalWarehouse:
    """Generate tiny data, ingest into :memory: warehouse, create views."""
    PROFILES[profile_name] = ProfileConfig(
        name=profile_name,
        n_parts=n_parts,
        n_suppliers=max(10, n_parts // 10),
        n_plants=2,
        warehouses_per_plant=1,
    )
    run_generation(
        profile_name, seed=seed, output_root=tmp_dir, inject=True, inject_rate=inject_rate
    )
    wh = LocalWarehouse(":memory:")
    svc = IngestionService(wh)
    svc.ingest_directory(tmp_dir / profile_name, profile=profile_name)
    svc.load_ground_truth(tmp_dir / profile_name / "ground_truth" / "labels.csv")
    for sql in TRANSFORM_SQL:
        wh.execute(sql)
    return wh
