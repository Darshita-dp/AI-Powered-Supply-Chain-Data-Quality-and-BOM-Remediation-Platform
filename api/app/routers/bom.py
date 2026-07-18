from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from api.app.auth import get_principal
from api.app.dependencies import get_warehouse
from bom_guardian.bom_graph import BomGraph
from bom_guardian.warehouse import LocalWarehouse

router = APIRouter(prefix="/bom", tags=["bom"], dependencies=[Depends(get_principal)])


def _graph(wh: LocalWarehouse) -> BomGraph:
    comps = wh.query(
        "SELECT parent_part_key AS parent_part_id, child_part_key AS child_part_id, "
        "quantity_per, bom_rel_key AS bom_component_id FROM core.fact_bom_relationship"
    )
    return BomGraph.from_components(comps)


def _require_node(graph: BomGraph, part_id: str) -> None:
    if part_id not in graph.g:
        raise HTTPException(404, detail=f"part {part_id} has no BOM relationships")


@router.get("/{part_id}/graph")
def bom_graph(
    part_id: str,
    depth: int = Query(3, ge=1, le=10),
    wh: LocalWarehouse = Depends(get_warehouse),
) -> dict:
    graph = _graph(wh)
    _require_node(graph, part_id)
    edges = graph.expand(part_id, max_depth=depth)
    nodes = sorted({part_id, *(e["parent"] for e in edges), *(e["child"] for e in edges)})
    parts = (
        wh.query(
            "SELECT part_key, description, lifecycle_status, category FROM core.dim_part "
            f"WHERE part_key IN ({', '.join(repr(n) for n in nodes)})"
        )
        if nodes
        else None
    )
    meta = {r["part_key"]: r for r in parts.to_dict("records")} if parts is not None else {}
    cycles = [c for c in graph.cycles() if any(n in c for n in nodes)]
    return {
        "root": part_id,
        "nodes": [
            {
                "id": n,
                "description": meta.get(n, {}).get("description"),
                "lifecycle_status": meta.get(n, {}).get("lifecycle_status"),
                "category": meta.get(n, {}).get("category"),
                "in_cycle": any(n in c for c in cycles),
            }
            for n in nodes
        ],
        "edges": edges,
        "cycles": cycles,
    }


@router.get("/{part_id}/dependencies")
def dependencies(part_id: str, wh: LocalWarehouse = Depends(get_warehouse)) -> dict:
    graph = _graph(wh)
    _require_node(graph, part_id)
    return {"part_id": part_id, "dependencies": graph.dependencies(part_id)}


@router.get("/{part_id}/reverse-dependencies")
def reverse_dependencies(part_id: str, wh: LocalWarehouse = Depends(get_warehouse)) -> dict:
    graph = _graph(wh)
    _require_node(graph, part_id)
    return {
        "part_id": part_id,
        "reverse_dependencies": graph.reverse_dependencies(part_id),
        "affected_assembly_count": graph.affected_assembly_count(part_id),
    }
