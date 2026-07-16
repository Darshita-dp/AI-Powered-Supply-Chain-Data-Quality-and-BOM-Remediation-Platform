"""Blast-radius calculation: the downstream operational and financial exposure
of a data-quality issue on one part.

All inputs are read-only DataFrames; nothing here mutates state.
"""

from __future__ import annotations

import pandas as pd

from bom_guardian.bom_graph import BomGraph
from bom_guardian.observability import get_logger

PRIORITY_WEIGHTS = {
    "assemblies": 2.0,  # per affected parent assembly
    "demand_qty": 0.01,  # per unit of exposed future demand
    "inventory_value": 0.001,  # per currency unit of exposed inventory
    "po_value": 0.001,  # per currency unit of open PO value
    "production_orders": 3.0,  # per affected production order
    "single_source": 10.0,  # bonus when supplier concentration is high
}


class ImpactTwin:
    """Computes the blast radius of an issue affecting a given part."""

    def __init__(
        self,
        graph: BomGraph,
        parts: pd.DataFrame,
        inventory: pd.DataFrame,
        future_demand: pd.DataFrame,
        po_lines: pd.DataFrame,
        production_orders: pd.DataFrame,
        supplier_parts: pd.DataFrame,
        revisions: pd.DataFrame | None = None,
    ) -> None:
        self.graph = graph
        self.parts = parts
        self.inventory = inventory
        self.future_demand = future_demand
        self.po_lines = po_lines
        self.production_orders = production_orders
        self.supplier_parts = supplier_parts
        self.revisions = revisions if revisions is not None else pd.DataFrame()
        self._log = get_logger("impact_twin")

    def blast_radius(self, part_id: str) -> dict:
        """Full downstream exposure for a defect on `part_id`."""
        upstream = self.graph.reverse_dependencies(part_id)  # assemblies above
        downstream = self.graph.dependencies(part_id)  # components below
        affected_parts = {part_id, *upstream}

        demand = self.future_demand[self.future_demand["part_id"].isin(affected_parts)]
        inventory = self.inventory[self.inventory["part_id"].isin(affected_parts)]
        pos = self.po_lines[self.po_lines["part_id"].isin(affected_parts)]
        prod = (
            self.production_orders[self.production_orders["part_id"].isin(affected_parts)]
            if not self.production_orders.empty
            else pd.DataFrame()
        )
        suppliers = self.supplier_parts[self.supplier_parts["part_id"].isin(affected_parts)][
            "supplier_id"
        ].unique()
        plants = (
            self.parts[self.parts["part_id"].isin(affected_parts)]["primary_plant"]
            .dropna()
            .unique()
        )
        revisions = (
            self.revisions[self.revisions["part_id"].isin(affected_parts)]
            if not self.revisions.empty
            else pd.DataFrame()
        )

        part_costs = self.parts.set_index("part_id")["standard_cost"]
        exposed_cost = float(sum(part_costs.get(p, 0.0) or 0.0 for p in affected_parts))
        concentration = self.graph.supplier_concentration(part_id, self.supplier_parts)

        result = {
            "part_id": part_id,
            "affected_parent_assemblies": len(upstream),
            "downstream_components": len(downstream),
            "dependency_depth": self.graph.depth(part_id),
            "future_demand_qty_exposed": float(demand["demand_qty"].sum())
            if not demand.empty
            else 0.0,
            "inventory_value_exposed": float(inventory["on_hand_value"].sum())
            if not inventory.empty
            else 0.0,
            "po_value_exposed": float(pos["line_value"].sum()) if not pos.empty else 0.0,
            "production_orders_affected": len(prod),
            "suppliers_affected": len(suppliers),
            "plants_affected": len(plants),
            "engineering_revisions_affected": len(revisions),
            "supplier_concentration": concentration,
            "estimated_cost_exposure": round(exposed_cost, 2),
        }
        result["operational_priority"] = self._priority(result)
        return result

    @staticmethod
    def _priority(r: dict) -> float:
        w = PRIORITY_WEIGHTS
        score = (
            r["affected_parent_assemblies"] * w["assemblies"]
            + r["future_demand_qty_exposed"] * w["demand_qty"]
            + r["inventory_value_exposed"] * w["inventory_value"]
            + r["po_value_exposed"] * w["po_value"]
            + r["production_orders_affected"] * w["production_orders"]
        )
        if r["supplier_concentration"].get("single_source_ratio", 0) > 0.5:
            score += w["single_source"]
        return round(score, 2)
