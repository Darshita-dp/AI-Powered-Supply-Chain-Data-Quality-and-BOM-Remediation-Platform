from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from api.app.dependencies import get_warehouse
from bom_guardian.copilot import Copilot
from bom_guardian.warehouse import LocalWarehouse

router = APIRouter(prefix="/copilot", tags=["copilot"])


class CopilotQuery(BaseModel):
    question: str = Field(min_length=3, max_length=500)


@router.post("/query")
def copilot_query(body: CopilotQuery, wh: LocalWarehouse = Depends(get_warehouse)) -> dict:
    answer = Copilot(wh).query(body.question)
    return {
        "question": answer.question,
        "classification": answer.classification,
        "answer": answer.answer,
        "rows": answer.rows[:25],
        "citations": answer.citations[:25],
        "insufficient_evidence": answer.insufficient_evidence,
        "refused": answer.refused,
    }
