"""Data-quality engine tests: rules detect injected defects, with evidence.

Uses the real pipeline (generate -> inject -> ingest -> minimal transform) on a
tiny profile so detection is measured against known ground truth.
"""

import pytest
from data_generator.config.profiles import PROFILES, ProfileConfig
from data_generator.orchestrator import run_generation

from bom_guardian.ingestion import IngestionService
from bom_guardian.quality import RULES, QualityScorer, RuleEngine
from bom_guardian.warehouse import LocalWarehouse

TINY = ProfileConfig(name="tiny", n_parts=300, n_suppliers=30, n_plants=2, warehouses_per_plant=1)

# Minimal stand-in for the dbt staging/core layers so quality tests do not
# depend on a dbt subprocess. Mirrors the dbt SQL for the columns rules use.
_TRANSFORM_SQL = [
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


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):  # type: ignore[no-untyped-def]
    PROFILES["tiny"] = TINY
    root = tmp_path_factory.mktemp("dq")
    run_generation("tiny", seed=11, output_root=root, inject=True, inject_rate=0.03)
    wh = LocalWarehouse(":memory:")
    svc = IngestionService(wh)
    svc.ingest_directory(root / "tiny", profile="tiny")
    svc.load_ground_truth(root / "tiny" / "ground_truth" / "labels.csv")
    for sql in _TRANSFORM_SQL:
        wh.execute(sql)
    yield wh
    wh.close()


@pytest.fixture(scope="module")
def run_summary(warehouse):  # type: ignore[no-untyped-def]
    return RuleEngine(warehouse).run_all()


def test_registry_has_at_least_40_rules() -> None:
    assert len(RULES) >= 40
    assert len({r.rule_id for r in RULES}) == len(RULES)


def test_all_rules_execute_without_failure(run_summary) -> None:  # type: ignore[no-untyped-def]
    assert run_summary["rules_failed"] == 0, run_summary["failed_rules"]
    assert run_summary["rules_executed"] >= 40


def test_issues_created_with_evidence(warehouse, run_summary) -> None:  # type: ignore[no-untyped-def]
    assert run_summary["issues_created"] > 0
    issues = warehouse.query("SELECT * FROM quality.dq_issues")
    evidence = warehouse.query("SELECT * FROM quality.dq_issue_evidence")
    assert len(evidence) == len(issues)
    assert issues["issue_id"].is_unique
    assert set(evidence["issue_id"]) == set(issues["issue_id"])


@pytest.mark.parametrize(
    ("issue_type", "rule_ids"),
    [
        ("invalid_uom", ["VALD-001"]),
        ("zero_component_quantity", ["VALD-006"]),
        ("negative_component_quantity", ["VALD-007"]),
        ("orphan_bom_component", ["REFI-002"]),
        ("orphan_bom_parent", ["REFI-001"]),
        ("self_referencing_bom", ["GRPH-001"]),
        ("blocked_part_with_future_demand", ["XFLD-003"]),
        ("invalid_plant_relationship", ["REFI-004"]),
        ("invalid_supplier_relationship", ["REFI-003"]),
        ("stale_record", ["TEMP-002"]),
    ],
)
def test_injected_defects_are_detected(warehouse, run_summary, issue_type, rule_ids) -> None:  # type: ignore[no-untyped-def]
    """Every injected defect record of these types must be flagged by its rule."""
    gt = warehouse.query(
        f"SELECT record_id FROM ground_truth.labels WHERE issue_type = '{issue_type}'"
    )
    detected = warehouse.query(
        "SELECT DISTINCT entity_key FROM quality.dq_issues "
        f"WHERE rule_id IN ({', '.join(repr(r) for r in rule_ids)})"
    )
    missing = set(gt["record_id"]) - set(detected["entity_key"])
    assert not missing, (
        f"{issue_type}: {len(missing)} injected defects undetected: {sorted(missing)[:5]}"
    )


def test_scoring_produces_all_levels(warehouse, run_summary) -> None:  # type: ignore[no-untyped-def]
    result = QualityScorer(warehouse).run_all()
    assert result["entities_scored"] > 0
    assert result["boms_scored"] > 0
    assert 0.0 <= result["enterprise_quality_score"] <= 100.0
    scores = warehouse.query("SELECT * FROM quality.entity_scores")
    assert scores["quality_score"].between(0, 100).all()


def test_rule_definitions_synced(warehouse, run_summary) -> None:  # type: ignore[no-untyped-def]
    rules = warehouse.query("SELECT * FROM quality.dq_rules")
    assert len(rules) >= 40
    assert rules["rule_id"].is_unique


def test_executions_recorded(warehouse, run_summary) -> None:  # type: ignore[no-untyped-def]
    execs = warehouse.query("SELECT * FROM quality.dq_rule_executions")
    assert len(execs) >= 40
    assert (execs["status"] == "COMPLETED").all()


def test_ground_truth_isolated_from_quality_tables(warehouse, run_summary) -> None:  # type: ignore[no-untyped-def]
    issues = warehouse.query("SELECT * FROM quality.dq_issues LIMIT 1")
    assert "injection_id" not in issues.columns
    assert "correct_value" not in issues.columns
