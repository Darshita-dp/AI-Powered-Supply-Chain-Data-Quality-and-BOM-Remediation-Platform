from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from api.app.dependencies import get_remediation_engine, get_warehouse
from api.app.schemas import DecisionIn, EvidenceOut, IssueOut, Page
from api.app.services import IssueService
from bom_guardian.ai import RemediationEngine
from bom_guardian.warehouse import LocalWarehouse

router = APIRouter(prefix="/issues", tags=["issues"])

_SORTABLE = {"issue_id", "rule_id", "severity", "domain", "status", "detected_at"}


def _safe(value: str) -> str:
    return value.replace("'", "''")


@router.get("", response_model=Page[IssueOut])
def list_issues(
    wh: LocalWarehouse = Depends(get_warehouse),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    severity: str | None = None,
    domain: str | None = None,
    rule_id: str | None = None,
    status: str | None = None,
    entity_key: str | None = None,
    sort_by: str = Query("detected_at"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
) -> Page[IssueOut]:
    if sort_by not in _SORTABLE:
        raise HTTPException(422, detail=f"sort_by must be one of {sorted(_SORTABLE)}")
    clauses = ["1=1"]
    for col, val in [
        ("severity", severity),
        ("domain", domain),
        ("rule_id", rule_id),
        ("status", status),
        ("entity_key", entity_key),
    ]:
        if val:
            clauses.append(f"{col} = '{_safe(val)}'")
    where = " AND ".join(clauses)
    total = int(wh.query(f"SELECT COUNT(*) AS n FROM quality.dq_issues WHERE {where}").iloc[0]["n"])
    rows = wh.query(
        f"SELECT * FROM quality.dq_issues WHERE {where} "
        f"ORDER BY {sort_by} {sort_dir.upper()} LIMIT {page_size} OFFSET {(page - 1) * page_size}"
    )
    items = [
        IssueOut(
            **{
                k: (str(r[k]) if k == "detected_at" and r.get(k) is not None else r.get(k))
                for k in IssueOut.model_fields
            }
        )
        for r in rows.to_dict("records")
    ]
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/{issue_id}")
def get_issue(issue_id: str, wh: LocalWarehouse = Depends(get_warehouse)) -> dict:
    issue = IssueService(wh).get_issue(issue_id)
    issue["detected_at"] = str(issue.get("detected_at"))
    return issue


@router.get("/{issue_id}/evidence", response_model=list[EvidenceOut])
def issue_evidence(issue_id: str, wh: LocalWarehouse = Depends(get_warehouse)) -> list[EvidenceOut]:
    IssueService(wh).get_issue(issue_id)
    df = wh.query(f"SELECT * FROM quality.dq_issue_evidence WHERE issue_id = '{_safe(issue_id)}'")
    return [
        EvidenceOut(**{k: r.get(k) for k in EvidenceOut.model_fields})
        for r in df.to_dict("records")
    ]


@router.get("/{issue_id}/history")
def issue_history(issue_id: str, wh: LocalWarehouse = Depends(get_warehouse)) -> list[dict]:
    svc = IssueService(wh)
    svc.get_issue(issue_id)
    history = svc.history(issue_id)
    for h in history:
        h["decided_at"] = str(h.get("decided_at"))
    return history


@router.post("/{issue_id}/recommendations")
def generate_recommendation(
    issue_id: str,
    engine: RemediationEngine = Depends(get_remediation_engine),
) -> dict:
    try:
        bundle = engine.gather_evidence(issue_id)
    except ValueError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    proposal = engine.propose(bundle)
    return proposal.model_dump()


@router.post("/{issue_id}/approve")
def approve(issue_id: str, body: DecisionIn, wh: LocalWarehouse = Depends(get_warehouse)) -> dict:
    return IssueService(wh).decide(issue_id, "APPROVE", body.reviewer, body.reason)


@router.post("/{issue_id}/reject")
def reject(issue_id: str, body: DecisionIn, wh: LocalWarehouse = Depends(get_warehouse)) -> dict:
    return IssueService(wh).decide(issue_id, "REJECT", body.reviewer, body.reason)


@router.post("/{issue_id}/request-evidence")
def request_evidence(
    issue_id: str, body: DecisionIn, wh: LocalWarehouse = Depends(get_warehouse)
) -> dict:
    return IssueService(wh).decide(issue_id, "REQUEST_EVIDENCE", body.reviewer, body.reason)
