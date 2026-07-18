from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from api.app.auth import get_principal
from api.app.dependencies import get_warehouse
from api.app.routers.parts import _build_twin
from api.app.schemas import ComponentReplacementIn, FieldCorrectionIn, MergeScenarioIn
from bom_guardian.impact_twin import ScenarioResult, ScenarioSimulator
from bom_guardian.warehouse import LocalWarehouse

router = APIRouter(
    prefix="/scenarios", tags=["scenarios"], dependencies=[Depends(get_principal)]
)


def _simulator(wh: LocalWarehouse) -> ScenarioSimulator:
    return ScenarioSimulator(_build_twin(wh), warehouse=wh)


def _out(result: ScenarioResult) -> dict:
    return {
        "scenario_id": result.scenario_id,
        "scenario_type": result.scenario_type,
        "parameters": result.parameters,
        "before": result.before,
        "after": result.after,
        "resolved_rules": result.resolved_rules,
        "new_warnings": result.new_warnings,
        "approval_required": result.approval_required,
    }


@router.post("/merge")
def simulate_merge(body: MergeScenarioIn, wh: LocalWarehouse = Depends(get_warehouse)) -> dict:
    return _out(_simulator(wh).merge_parts(body.duplicate_id, body.surviving_id))


@router.post("/field-correction")
def simulate_field_correction(
    body: FieldCorrectionIn, wh: LocalWarehouse = Depends(get_warehouse)
) -> dict:
    return _out(_simulator(wh).field_correction(body.part_id, body.field, body.new_value))


@router.post("/component-replacement")
def simulate_component_replacement(
    body: ComponentReplacementIn, wh: LocalWarehouse = Depends(get_warehouse)
) -> dict:
    return _out(
        _simulator(wh).component_replacement(body.parent_id, body.old_child_id, body.new_child_id)
    )


@router.get("/{scenario_id}")
def get_scenario(scenario_id: str, wh: LocalWarehouse = Depends(get_warehouse)) -> dict:
    df = wh.query(
        "SELECT * FROM quality.scenarios WHERE scenario_id = "
        f"'{scenario_id.replace(chr(39), chr(39) * 2)}'"
    )
    if df.empty:
        raise HTTPException(404, detail=f"scenario {scenario_id} not found")
    row = df.iloc[0].to_dict()
    for key in ("parameters", "before_state", "after_state", "resolved_rules", "new_warnings"):
        row[key] = json.loads(row[key])
    row["created_at"] = str(row["created_at"])
    return row
