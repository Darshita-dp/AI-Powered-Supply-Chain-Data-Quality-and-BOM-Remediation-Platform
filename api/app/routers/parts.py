from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from api.app.dependencies import get_warehouse
from api.app.schemas import Page, PartOut
from bom_guardian.bom_graph import BomGraph
from bom_guardian.golden_record import GoldenRecordBuilder
from bom_guardian.impact_twin import ImpactTwin
from bom_guardian.warehouse import LocalWarehouse

router = APIRouter(prefix="/parts", tags=["parts"])

_SORTABLE = {"part_key", "description", "category", "lifecycle_status", "standard_cost"}


def _safe(value: str) -> str:
    return value.replace("'", "''")


@router.get("", response_model=Page[PartOut])
def list_parts(
    wh: LocalWarehouse = Depends(get_warehouse),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    search: str | None = None,
    category: str | None = None,
    lifecycle_status: str | None = None,
    plant: str | None = None,
    sort_by: str = Query("part_key"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
) -> Page[PartOut]:
    if sort_by not in _SORTABLE:
        raise HTTPException(422, detail=f"sort_by must be one of {sorted(_SORTABLE)}")
    clauses = ["1=1"]
    if search:
        s = _safe(search.upper())
        clauses.append(
            f"(upper(coalesce(description,'')) LIKE '%{s}%' "
            f"OR upper(coalesce(source_part_number,'')) LIKE '%{s}%' OR part_key LIKE '%{s}%')"
        )
    if category:
        clauses.append(f"category = '{_safe(category.upper())}'")
    if lifecycle_status:
        clauses.append(f"lifecycle_status = '{_safe(lifecycle_status.upper())}'")
    if plant:
        clauses.append(f"primary_plant = '{_safe(plant.upper())}'")
    where = " AND ".join(clauses)
    total = int(wh.query(f"SELECT COUNT(*) AS n FROM core.dim_part WHERE {where}").iloc[0]["n"])
    rows = wh.query(
        f"SELECT * FROM core.dim_part WHERE {where} "
        f"ORDER BY {sort_by} {sort_dir.upper()} "
        f"LIMIT {page_size} OFFSET {(page - 1) * page_size}"
    )
    items = [
        PartOut(**{k: (None if pd.isna(r.get(k)) else r.get(k)) for k in PartOut.model_fields})
        for r in rows.to_dict("records")
    ]
    return Page(items=items, total=total, page=page, page_size=page_size)


def _get_part_row(wh: LocalWarehouse, part_id: str) -> dict:
    df = wh.query(f"SELECT * FROM core.dim_part WHERE part_key = '{_safe(part_id)}'")
    if df.empty:
        raise HTTPException(404, detail=f"part {part_id} not found")
    return df.iloc[0].to_dict()


@router.get("/{part_id}")
def get_part(part_id: str, wh: LocalWarehouse = Depends(get_warehouse)) -> dict:
    row = _get_part_row(wh, part_id)
    return {k: (None if pd.isna(v) else v) for k, v in row.items()}


@router.get("/{part_id}/sources")
def part_sources(part_id: str, wh: LocalWarehouse = Depends(get_warehouse)) -> list[dict]:
    _get_part_row(wh, part_id)
    aliases = wh.query(f"SELECT * FROM raw.part_aliases WHERE part_id = '{_safe(part_id)}'")
    return aliases.to_dict("records")


@router.get("/{part_id}/lineage")
def part_lineage(part_id: str, wh: LocalWarehouse = Depends(get_warehouse)) -> dict:
    """Field-level golden-record lineage built over the duplicate cluster of this part."""
    _get_part_row(wh, part_id)
    cluster = wh.query(
        "SELECT p.part_key AS part_id, p.source_part_number, p.source_system, p.description, "
        "p.category, p.uom, p.lifecycle_status, p.manufacturer_part_number, p.standard_cost, "
        "p.lead_time_days, p.primary_plant, p.last_updated "
        "FROM core.dim_part p WHERE p.part_number_normalized = ("
        f"SELECT part_number_normalized FROM core.dim_part WHERE part_key = '{_safe(part_id)}')"
    )
    golden = GoldenRecordBuilder().build(cluster, entity_id=f"GLD-{part_id}")
    return {
        "entity_id": golden.entity_id,
        "members": golden.member_record_ids,
        "fields": {
            name: {
                "selected_value": d.selected_value,
                "source_record": d.source_record,
                "source_system": d.source_system,
                "reason": d.reason,
                "confidence": d.confidence,
                "alternatives": [
                    {"value": a.value, "source_record": a.source_record, "score": a.score}
                    for a in d.alternatives
                ],
            }
            for name, d in golden.fields.items()
        },
    }


def _build_twin(wh: LocalWarehouse) -> ImpactTwin:
    comps = wh.query(
        "SELECT parent_part_key AS parent_part_id, child_part_key AS child_part_id, "
        "quantity_per, bom_rel_key AS bom_component_id FROM core.fact_bom_relationship"
    )
    parts = wh.query(
        "SELECT part_key AS part_id, standard_cost, primary_plant, description, "
        "lifecycle_status, uom FROM core.dim_part"
    )
    inventory = wh.query("SELECT part_key AS part_id, on_hand_value FROM core.fact_inventory")
    demand = wh.query("SELECT part_key AS part_id, demand_qty FROM core.fact_future_demand")
    po = wh.query("SELECT part_key AS part_id, line_value FROM core.fact_purchase_order")
    prod = wh.query("SELECT part_id, status FROM raw.production_orders")
    sp = wh.query("SELECT part_id, supplier_id FROM raw.supplier_parts")
    return ImpactTwin(
        graph=BomGraph.from_components(comps),
        parts=parts,
        inventory=inventory,
        future_demand=demand,
        po_lines=po,
        production_orders=prod,
        supplier_parts=sp,
    )


@router.get("/{part_id}/impact")
def part_impact(part_id: str, wh: LocalWarehouse = Depends(get_warehouse)) -> dict:
    _get_part_row(wh, part_id)
    return _build_twin(wh).blast_radius(part_id)
