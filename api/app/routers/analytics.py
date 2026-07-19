from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends

from api.app.auth import get_principal
from api.app.dependencies import get_warehouse
from bom_guardian.quality import QualityScorer
from bom_guardian.warehouse import LocalWarehouse

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(get_principal)])


@router.get("/quality")
def quality_analytics(wh: LocalWarehouse = Depends(get_warehouse)) -> dict:
    enterprise = QualityScorer(wh).enterprise_score()
    by_severity = wh.query(
        "SELECT severity, COUNT(*) AS n FROM quality.dq_issues "
        "WHERE status NOT IN ('CLOSED', 'REJECTED') GROUP BY 1"
    )
    by_domain = wh.query(
        "SELECT domain, COUNT(*) AS n FROM quality.dq_issues "
        "WHERE status NOT IN ('CLOSED', 'REJECTED') GROUP BY 1 ORDER BY n DESC"
    )
    by_rule = wh.query(
        "SELECT rule_id, COUNT(*) AS n FROM quality.dq_issues GROUP BY 1 ORDER BY n DESC LIMIT 10"
    )
    return {
        **enterprise,
        "open_by_severity": dict(
            zip(by_severity["severity"], by_severity["n"].astype(int), strict=True)
        ),
        "open_by_domain": dict(zip(by_domain["domain"], by_domain["n"].astype(int), strict=True)),
        "top_rules": by_rule.to_dict("records"),
    }


@router.get("/business-impact")
def business_impact(wh: LocalWarehouse = Depends(get_warehouse)) -> dict:
    inv = wh.query("SELECT SUM(on_hand_value) AS v FROM core.fact_inventory").iloc[0]["v"]
    demand = wh.query("SELECT SUM(demand_qty) AS q FROM core.fact_future_demand").iloc[0]["q"]
    critical_entities = wh.query(
        "SELECT COUNT(DISTINCT entity_key) AS n FROM quality.dq_issues "
        "WHERE severity = 'critical' AND status NOT IN ('CLOSED', 'REJECTED')"
    ).iloc[0]["n"]
    return {
        "total_inventory_value": float(inv or 0),
        "total_future_demand_qty": float(demand or 0),
        "entities_with_critical_issues": int(critical_entities),
    }


@router.get("/remediation")
def remediation_analytics(wh: LocalWarehouse = Depends(get_warehouse)) -> dict:
    try:
        decisions = wh.query(
            "SELECT decision, COUNT(*) AS n FROM quality.remediation_decisions GROUP BY 1"
        )
    except Exception:
        decisions = pd.DataFrame(columns=["decision", "n"])
    counts = dict(zip(decisions["decision"], decisions["n"].astype(int), strict=True))
    approved = counts.get("APPROVE", 0)
    rejected = counts.get("REJECT", 0)
    total = approved + rejected
    return {
        "decisions": counts,
        "acceptance_rate": round(approved / total, 4) if total else None,
        "backlog": int(
            wh.query(
                "SELECT COUNT(*) AS n FROM quality.dq_issues "
                "WHERE status IN ('DETECTED', 'PENDING_REVIEW')"
            ).iloc[0]["n"]
        ),
    }


@router.get("/ai-governance")
def ai_governance(wh: LocalWarehouse = Depends(get_warehouse)) -> dict:
    try:
        calls = wh.query("SELECT * FROM quality.ai_call_audit")
    except Exception:
        return {"calls": 0}
    if calls.empty:
        return {"calls": 0}
    return {
        "calls": len(calls),
        "by_provider": calls.groupby("provider").size().to_dict(),
        "abstention_rate": round(float(calls["abstained"].mean()), 4),
        "validation_failure_rate": round(float((calls["validation_result"] != "valid").mean()), 4),
        "avg_latency_ms": round(float(calls["latency_ms"].mean()), 2),
        "avg_confidence": round(float(calls["confidence"].mean()), 4),
        "prompt_versions": sorted(calls["prompt_version"].unique().tolist()),
    }
