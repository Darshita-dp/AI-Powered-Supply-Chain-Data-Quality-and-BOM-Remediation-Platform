"""Counterfactual remediation scenarios with before/after comparison.

Simulations work exclusively on copies of the input frames. The originals are
never mutated (verified by tests), and scenario results are persisted to a
dedicated quality.scenarios table — never to core/golden tables.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pandas as pd

from bom_guardian.bom_graph import BomGraph
from bom_guardian.impact_twin.blast_radius import ImpactTwin
from bom_guardian.observability import get_logger
from bom_guardian.warehouse import LocalWarehouse

_SCENARIO_DDL = """
CREATE TABLE IF NOT EXISTS quality.scenarios (
    scenario_id VARCHAR, scenario_type VARCHAR, parameters VARCHAR,
    before_state VARCHAR, after_state VARCHAR, resolved_rules VARCHAR,
    new_warnings VARCHAR, approval_required BOOLEAN, created_at TIMESTAMP
)
"""

VALID_UOMS = {"EA", "KG", "G", "M", "CM", "MM", "L", "ML", "M2", "SET", "PR", "ROL"}


@dataclass
class ScenarioResult:
    scenario_id: str
    scenario_type: str
    parameters: dict
    before: dict
    after: dict
    resolved_rules: list[str] = field(default_factory=list)
    new_warnings: list[str] = field(default_factory=list)
    approval_required: bool = True


class ScenarioSimulator:
    """Simulates merges, field corrections, and component replacements."""

    def __init__(self, twin: ImpactTwin, warehouse: LocalWarehouse | None = None) -> None:
        self.twin = twin
        self.wh = warehouse
        self._log = get_logger("scenario_simulator")
        if self.wh is not None:
            self.wh.execute(_SCENARIO_DDL)

    # ------------------------------------------------------------------
    def merge_parts(self, duplicate_id: str, surviving_id: str) -> ScenarioResult:
        """Simulate merging `duplicate_id` into `surviving_id`."""
        parts = self.twin.parts
        before = {
            "duplicate_record": self._part_summary(duplicate_id),
            "surviving_record": self._part_summary(surviving_id),
            "duplicate_impact": self.twin.blast_radius(duplicate_id),
        }
        # after-state on copies: repoint BOM edges and supplier links
        comps_after = self._components_copy()
        comps_after.loc[comps_after["child_part_id"] == duplicate_id, "child_part_id"] = (
            surviving_id
        )
        comps_after.loc[comps_after["parent_part_id"] == duplicate_id, "parent_part_id"] = (
            surviving_id
        )
        sp_after = self.twin.supplier_parts.copy()
        sp_after.loc[sp_after["part_id"] == duplicate_id, "part_id"] = surviving_id

        graph_after = BomGraph.from_components(comps_after)
        warnings: list[str] = []
        surviving = parts[parts["part_id"] == surviving_id]
        if not surviving.empty and surviving.iloc[0].get("lifecycle_status") != "ACTIVE":
            warnings.append(
                f"surviving record {surviving_id} is "
                f"{surviving.iloc[0].get('lifecycle_status')} — merge would route demand "
                "to a non-active part"
            )
        if not graph_after.is_acyclic():
            warnings.append("merge introduces a BOM cycle")

        after = {
            "repointed_bom_relationships": int(
                (self._components_copy()["child_part_id"] == duplicate_id).sum()
                + (self._components_copy()["parent_part_id"] == duplicate_id).sum()
            ),
            "repointed_supplier_links": int(
                (self.twin.supplier_parts["part_id"] == duplicate_id).sum()
            ),
            "surviving_impact": self._impact_with(graph_after, sp_after, surviving_id),
        }
        return self._finish(
            "merge",
            {"duplicate_id": duplicate_id, "surviving_id": surviving_id},
            before,
            after,
            resolved_rules=["UNIQ-002"],
            new_warnings=warnings,
        )

    def field_correction(self, part_id: str, fld: str, new_value: str) -> ScenarioResult:
        parts = self.twin.parts
        row = parts[parts["part_id"] == part_id]
        current = None if row.empty else row.iloc[0].get(fld)
        before = {"part": self._part_summary(part_id), "field": fld, "current_value": current}
        warnings: list[str] = []
        resolved: list[str] = []
        if fld == "uom":
            if new_value in VALID_UOMS:
                resolved.append("VALD-001")
            else:
                warnings.append(f"proposed UOM '{new_value}' is not in the governed list")
        if fld == "standard_cost":
            try:
                if float(new_value) <= 0:
                    warnings.append("proposed standard cost is non-positive (VALD-004)")
                else:
                    resolved.append("VALD-004")
            except ValueError:
                warnings.append("proposed standard cost is not numeric")
        after = {
            "field": fld,
            "proposed_value": new_value,
            "impact": self.twin.blast_radius(part_id),
        }
        return self._finish(
            "field_correction",
            {"part_id": part_id, "field": fld, "new_value": new_value},
            before,
            after,
            resolved_rules=resolved,
            new_warnings=warnings,
        )

    def component_replacement(
        self, parent_id: str, old_child_id: str, new_child_id: str
    ) -> ScenarioResult:
        parts = self.twin.parts
        before = {
            "parent": self._part_summary(parent_id),
            "old_component": self._part_summary(old_child_id),
            "old_component_impact": self.twin.blast_radius(old_child_id),
        }
        comps_after = self._components_copy()
        mask = (comps_after["parent_part_id"] == parent_id) & (
            comps_after["child_part_id"] == old_child_id
        )
        replaced = int(mask.sum())
        comps_after.loc[mask, "child_part_id"] = new_child_id
        graph_after = BomGraph.from_components(comps_after)

        warnings: list[str] = []
        resolved: list[str] = []
        new_child = parts[parts["part_id"] == new_child_id]
        old_child = parts[parts["part_id"] == old_child_id]
        if not old_child.empty and old_child.iloc[0].get("lifecycle_status") == "OBSOLETE":
            resolved.append("XFLD-004")
        if new_child.empty:
            warnings.append(f"replacement part {new_child_id} does not exist (REFI-002)")
        elif new_child.iloc[0].get("lifecycle_status") in ("OBSOLETE", "BLOCKED"):
            warnings.append(
                f"replacement part {new_child_id} is {new_child.iloc[0]['lifecycle_status']}"
            )
        if not graph_after.is_acyclic():
            warnings.append("replacement introduces a BOM cycle")

        after = {
            "relationships_replaced": replaced,
            "new_component": self._part_summary(new_child_id),
            "parent_impact_after": self._impact_with(
                graph_after, self.twin.supplier_parts, parent_id
            ),
        }
        return self._finish(
            "component_replacement",
            {"parent_id": parent_id, "old_child_id": old_child_id, "new_child_id": new_child_id},
            before,
            after,
            resolved_rules=resolved,
            new_warnings=warnings,
        )

    # ------------------------------------------------------------------
    def _components_copy(self) -> pd.DataFrame:
        rows = [
            {
                "parent_part_id": u,
                "child_part_id": v,
                "quantity_per": d.get("quantity_per", 1.0),
                "bom_component_id": d.get("bom_component_id", ""),
            }
            for u, v, d in self.twin.graph.g.edges(data=True)
        ]
        return pd.DataFrame(rows)

    def _impact_with(self, graph: BomGraph, supplier_parts: pd.DataFrame, part_id: str) -> dict:
        twin_after = ImpactTwin(
            graph=graph,
            parts=self.twin.parts,
            inventory=self.twin.inventory,
            future_demand=self.twin.future_demand,
            po_lines=self.twin.po_lines,
            production_orders=self.twin.production_orders,
            supplier_parts=supplier_parts,
            revisions=self.twin.revisions,
        )
        return twin_after.blast_radius(part_id)

    def _part_summary(self, part_id: str) -> dict:
        row = self.twin.parts[self.twin.parts["part_id"] == part_id]
        if row.empty:
            return {"part_id": part_id, "exists": False}
        r = row.iloc[0]
        return {
            "part_id": part_id,
            "exists": True,
            "description": r.get("description"),
            "lifecycle_status": r.get("lifecycle_status"),
            "uom": r.get("uom"),
            "standard_cost": r.get("standard_cost"),
        }

    def _finish(
        self,
        scenario_type: str,
        parameters: dict,
        before: dict,
        after: dict,
        resolved_rules: list[str],
        new_warnings: list[str],
    ) -> ScenarioResult:
        result = ScenarioResult(
            scenario_id=f"SCN-{uuid.uuid4().hex[:12]}",
            scenario_type=scenario_type,
            parameters=parameters,
            before=before,
            after=after,
            resolved_rules=resolved_rules,
            new_warnings=new_warnings,
            approval_required=True,
        )
        if self.wh is not None:

            def esc(obj: object) -> str:
                return json.dumps(obj, default=str).replace("'", "''")

            self.wh.execute(
                "INSERT INTO quality.scenarios VALUES ("
                f"'{result.scenario_id}', '{scenario_type}', '{esc(parameters)}', "
                f"'{esc(before)}', '{esc(after)}', '{esc(resolved_rules)}', "
                f"'{esc(new_warnings)}', TRUE, '{datetime.now(UTC).isoformat()}')"
            )
        self._log.info(
            "scenario_simulated",
            scenario_id=result.scenario_id,
            type=scenario_type,
            warnings=len(new_warnings),
        )
        return result
