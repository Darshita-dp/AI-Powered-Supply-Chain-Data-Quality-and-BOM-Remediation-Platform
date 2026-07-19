from __future__ import annotations

from fastapi import APIRouter, Depends

from api.app.auth import Principal, get_principal
from api.app.dependencies import get_warehouse
from bom_guardian import __version__
from bom_guardian.warehouse import LocalWarehouse

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@router.get("/readiness")
def readiness(wh: LocalWarehouse = Depends(get_warehouse)) -> dict:
    layout = wh.validate()
    return {"status": "ready", "schemas": {k: len(v) for k, v in layout.items()}}


@router.get("/me")
def me(principal: Principal = Depends(get_principal)) -> dict:
    """The authenticated principal. The UI shows this as the actor that will be
    recorded on a decision — reviewer identity is never typed in by the user."""
    return {"username": principal.username, "role": principal.role.value}


@router.get("/metrics")
def metrics(wh: LocalWarehouse = Depends(get_warehouse)) -> dict:
    issues = wh.query("SELECT status, COUNT(*) AS n FROM quality.dq_issues GROUP BY 1")
    return {
        "parts": wh.count("core", "dim_part"),
        "open_issues_by_status": dict(zip(issues["status"], issues["n"].astype(int), strict=True)),
    }
