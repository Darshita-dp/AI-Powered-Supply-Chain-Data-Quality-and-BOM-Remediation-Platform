"""Allowlisted read-only copilot tools.

Every tool runs a fixed, parameterized SELECT against the warehouse and returns
data plus citations (table + record ids). There is no free-form SQL path: the
copilot can only call these functions, and none of them can write.
"""

from __future__ import annotations

from bom_guardian.warehouse import LocalWarehouse


def _esc(value: str) -> str:
    return value.replace("'", "''")


def issues_for_entity(wh: LocalWarehouse, entity_key: str) -> dict:
    df = wh.query(
        "SELECT issue_id, rule_id, severity, domain, status, field "
        f"FROM quality.dq_issues WHERE entity_key = '{_esc(entity_key)}' "
        "ORDER BY severity"
    )
    return {
        "rows": df.to_dict("records"),
        "citations": [f"quality.dq_issues:{i}" for i in df["issue_id"].tolist()],
    }


def failed_rules_for_entity(wh: LocalWarehouse, entity_key: str) -> dict:
    df = wh.query(
        "SELECT DISTINCT i.rule_id, r.name, i.severity "
        "FROM quality.dq_issues i JOIN quality.dq_rules r ON r.rule_id = i.rule_id "
        f"WHERE i.entity_key = '{_esc(entity_key)}'"
    )
    return {
        "rows": df.to_dict("records"),
        "citations": [f"quality.dq_rules:{r}" for r in df["rule_id"].tolist()],
    }


def duplicate_explanation(wh: LocalWarehouse, entity_key: str) -> dict:
    df = wh.query(
        "SELECT i.issue_id, i.rule_id, e.failed_value "
        "FROM quality.dq_issues i "
        "JOIN quality.dq_issue_evidence e ON e.issue_id = i.issue_id "
        f"WHERE i.entity_key = '{_esc(entity_key)}' AND i.rule_id LIKE 'UNIQ-%'"
    )
    return {
        "rows": df.to_dict("records"),
        "citations": [f"quality.dq_issue_evidence:{i}" for i in df["issue_id"].tolist()],
    }


def assemblies_depending_on(wh: LocalWarehouse, part_id: str) -> dict:
    df = wh.query(
        "WITH RECURSIVE up AS ("
        f"  SELECT parent_part_key AS p FROM core.fact_bom_relationship "
        f"  WHERE child_part_key = '{_esc(part_id)}' "
        "  UNION "
        "  SELECT b.parent_part_key FROM core.fact_bom_relationship b "
        "  JOIN up ON b.child_part_key = up.p"
        ") SELECT DISTINCT p AS assembly FROM up"
    )
    return {
        "rows": df.to_dict("records"),
        "citations": [f"core.fact_bom_relationship:{part_id}"],
    }


def obsolete_components_by_demand(wh: LocalWarehouse, limit: int = 10) -> dict:
    df = wh.query(
        "SELECT p.part_key, SUM(d.demand_qty) AS demand_qty "
        "FROM core.dim_part p JOIN core.fact_future_demand d ON d.part_key = p.part_key "
        "WHERE p.lifecycle_status = 'OBSOLETE' "
        f"GROUP BY 1 ORDER BY 2 DESC LIMIT {int(limit)}"
    )
    return {
        "rows": df.to_dict("records"),
        "citations": [f"core.dim_part:{p}" for p in df["part_key"].tolist()],
    }


def supplier_risk_exposure(wh: LocalWarehouse, limit: int = 10) -> dict:
    df = wh.query(
        "SELECT sp.supplier_id, COUNT(DISTINCT i.issue_id) AS open_issues "
        "FROM quality.dq_issues i "
        "JOIN raw.supplier_parts sp ON sp.part_id = i.entity_key "
        "WHERE i.status NOT IN ('CLOSED', 'REJECTED') "
        f"GROUP BY 1 ORDER BY 2 DESC LIMIT {int(limit)}"
    )
    return {
        "rows": df.to_dict("records"),
        "citations": [f"raw.supplier_parts:{s}" for s in df["supplier_id"].tolist()],
    }


def issues_for_plant(wh: LocalWarehouse, plant: str, limit: int = 15) -> dict:
    df = wh.query(
        "SELECT i.issue_id, i.rule_id, i.severity, i.entity_key "
        "FROM quality.dq_issues i JOIN core.dim_part p ON p.part_key = i.entity_key "
        f"WHERE p.primary_plant = '{_esc(plant.upper())}' "
        "AND i.severity IN ('critical', 'high') "
        f"ORDER BY i.severity LIMIT {int(limit)}"
    )
    return {
        "rows": df.to_dict("records"),
        "citations": [f"quality.dq_issues:{i}" for i in df["issue_id"].tolist()],
    }


def ai_abstentions(wh: LocalWarehouse, limit: int = 10) -> dict:
    df = wh.query(
        "SELECT call_id, issue_id, provider, confidence, called_at "
        f"FROM quality.ai_call_audit WHERE abstained ORDER BY called_at DESC LIMIT {int(limit)}"
    )
    return {
        "rows": df.to_dict("records"),
        "citations": [f"quality.ai_call_audit:{c}" for c in df["call_id"].tolist()],
    }
