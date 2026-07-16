"""API services: issue lifecycle + audit over the quality schema."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException

from bom_guardian.warehouse import LocalWarehouse

_DECISION_DDL = """
CREATE TABLE IF NOT EXISTS quality.remediation_decisions (
    decision_id VARCHAR, issue_id VARCHAR, reviewer VARCHAR, decision VARCHAR,
    reason VARCHAR, before_status VARCHAR, after_status VARCHAR, decided_at TIMESTAMP
)
"""

# lifecycle: DETECTED -> ... -> PENDING_REVIEW -> APPROVED/REJECTED -> ... -> CLOSED
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "APPROVE": {
        "DETECTED",
        "ENRICHED",
        "PRIORITIZED",
        "RECOMMENDATION_GENERATED",
        "PENDING_REVIEW",
    },
    "REJECT": {"DETECTED", "ENRICHED", "PRIORITIZED", "RECOMMENDATION_GENERATED", "PENDING_REVIEW"},
    "REQUEST_EVIDENCE": {
        "DETECTED",
        "ENRICHED",
        "PRIORITIZED",
        "RECOMMENDATION_GENERATED",
        "PENDING_REVIEW",
    },
}
DECISION_TO_STATUS = {
    "APPROVE": "APPROVED",
    "REJECT": "REJECTED",
    "REQUEST_EVIDENCE": "PENDING_REVIEW",
}


class IssueService:
    def __init__(self, wh: LocalWarehouse) -> None:
        self.wh = wh
        self.wh.execute(_DECISION_DDL)

    def get_issue(self, issue_id: str) -> dict:
        df = self.wh.query(
            f"SELECT * FROM quality.dq_issues WHERE issue_id = '{self._safe(issue_id)}'"
        )
        if df.empty:
            raise HTTPException(status_code=404, detail=f"issue {issue_id} not found")
        return df.iloc[0].to_dict()

    def decide(self, issue_id: str, decision: str, reviewer: str, reason: str) -> dict:
        """Record a human decision and transition the issue. Humans only —
        this is the sole code path that changes an issue toward APPROVED."""
        issue = self.get_issue(issue_id)
        before = str(issue["status"])
        if before not in ALLOWED_TRANSITIONS[decision]:
            raise HTTPException(
                status_code=409,
                detail=f"cannot {decision} an issue in status {before}",
            )
        after = DECISION_TO_STATUS[decision]
        did = f"DEC-{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC).isoformat()
        self.wh.execute(
            "INSERT INTO quality.remediation_decisions VALUES "
            f"('{did}', '{self._safe(issue_id)}', '{self._safe(reviewer)}', '{decision}', "
            f"'{self._safe(reason)}', '{before}', '{after}', '{now}')"
        )
        self.wh.execute(
            f"UPDATE quality.dq_issues SET status = '{after}' "
            f"WHERE issue_id = '{self._safe(issue_id)}'"
        )
        return {"decision_id": did, "issue_id": issue_id, "status": after}

    def history(self, issue_id: str) -> list[dict]:
        df = self.wh.query(
            "SELECT * FROM quality.remediation_decisions "
            f"WHERE issue_id = '{self._safe(issue_id)}' ORDER BY decided_at"
        )
        return df.to_dict(orient="records")

    @staticmethod
    def _safe(value: str) -> str:
        return value.replace("'", "''")
