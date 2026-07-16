"""BOM as a directed graph: parent assembly -> child component (NetworkX).

Provides structural validation (cycles, self-references, orphans), traversal
(dependencies, reverse dependencies, paths, subassembly expansion), and
importance measures (centrality, criticality, affected-assembly counts).
"""

from __future__ import annotations

from typing import Any

import networkx as nx
import pandas as pd

from bom_guardian.observability import get_logger


class BomGraph:
    """Directed BOM graph. Edges carry quantity_per and relationship metadata."""

    def __init__(self, graph: nx.DiGraph) -> None:
        self.g = graph
        self._log = get_logger("bom_graph")

    @classmethod
    def from_components(cls, components: pd.DataFrame) -> BomGraph:
        """Build from a bom_components-shaped frame
        (parent_part_id, child_part_id, quantity_per, bom_component_id)."""
        g = nx.DiGraph()
        for _, row in components.iterrows():
            g.add_edge(
                str(row["parent_part_id"]),
                str(row["child_part_id"]),
                quantity_per=float(row.get("quantity_per") or 0.0),
                bom_component_id=str(row.get("bom_component_id") or ""),
            )
        return cls(g)

    # ---------------- validation ----------------
    def self_references(self) -> list[str]:
        return [n for n in self.g.nodes if self.g.has_edge(n, n)]

    def cycles(self) -> list[list[str]]:
        """All simple cycles (self-references excluded — reported separately)."""
        return [c for c in nx.simple_cycles(self.g) if len(c) > 1]

    def is_acyclic(self) -> bool:
        return nx.is_directed_acyclic_graph(self.g)

    def orphans(self, known_part_ids: set[str]) -> dict[str, list[str]]:
        """Graph nodes not present in the part master, split by role."""
        missing = [n for n in self.g.nodes if n not in known_part_ids]
        return {
            "missing_parents": [n for n in missing if self.g.out_degree(n) > 0],
            "missing_children": [n for n in missing if self.g.out_degree(n) == 0],
        }

    def validate(self, known_part_ids: set[str] | None = None) -> dict[str, Any]:
        report: dict[str, Any] = {
            "nodes": self.g.number_of_nodes(),
            "edges": self.g.number_of_edges(),
            "is_acyclic": self.is_acyclic(),
            "self_references": self.self_references(),
            "cycles": self.cycles(),
            "connected_components": nx.number_weakly_connected_components(self.g),
        }
        if known_part_ids is not None:
            report["orphans"] = self.orphans(known_part_ids)
        return report

    # ---------------- structure ----------------
    def roots(self) -> list[str]:
        """Top-level assemblies: have children, no parents."""
        return sorted(
            n for n in self.g.nodes if self.g.in_degree(n) == 0 and self.g.out_degree(n) > 0
        )

    def leaves(self) -> list[str]:
        """Pure components: no children."""
        return sorted(n for n in self.g.nodes if self.g.out_degree(n) == 0)

    def depth(self, part_id: str) -> int:
        """Longest chain below a part (0 for a leaf)."""
        if part_id not in self.g:
            return 0
        sub_nodes = nx.descendants(self.g, part_id) | {part_id}
        sub = self.g.subgraph(sub_nodes)
        if not nx.is_directed_acyclic_graph(sub):
            # bounded BFS depth when a cycle corrupts the subtree
            return len(dict(nx.bfs_predecessors(self.g, part_id)))
        return int(nx.dag_longest_path_length(sub))

    def max_depth(self) -> int:
        return max((self.depth(r) for r in self.roots()), default=0)

    # ---------------- traversal ----------------
    def dependencies(self, part_id: str) -> list[str]:
        """All downstream components of a part."""
        if part_id not in self.g:
            return []
        return sorted(nx.descendants(self.g, part_id))

    def reverse_dependencies(self, part_id: str) -> list[str]:
        """All upstream parents/assemblies that (transitively) use this part."""
        if part_id not in self.g:
            return []
        return sorted(nx.ancestors(self.g, part_id))

    def affected_assembly_count(self, part_id: str) -> int:
        return len(self.reverse_dependencies(part_id))

    def paths(self, from_part: str, to_part: str, limit: int = 25) -> list[list[str]]:
        """Dependency paths from an assembly down to a component (bounded)."""
        if from_part not in self.g or to_part not in self.g:
            return []
        out: list[list[str]] = []
        for path in nx.all_simple_paths(self.g, from_part, to_part):
            out.append(path)
            if len(out) >= limit:
                break
        return out

    def expand(self, part_id: str, max_depth: int | None = None) -> list[dict]:
        """Subassembly expansion: BFS with level and quantity-per edges."""
        if part_id not in self.g:
            return []
        rows: list[dict] = []
        frontier = [(part_id, 0)]
        seen = {part_id}
        while frontier:
            node, level = frontier.pop(0)
            if max_depth is not None and level >= max_depth:
                continue
            for child in self.g.successors(node):
                rows.append(
                    {
                        "parent": node,
                        "child": child,
                        "level": level + 1,
                        "quantity_per": self.g.edges[node, child].get("quantity_per"),
                    }
                )
                if child not in seen:
                    seen.add(child)
                    frontier.append((child, level + 1))
        return rows

    # ---------------- importance ----------------
    def centrality(self, top_n: int | None = None) -> dict[str, float]:
        """Degree centrality — cheap, interpretable 'how shared is this node'."""
        cent = nx.degree_centrality(self.g)
        ranked = dict(sorted(cent.items(), key=lambda kv: kv[1], reverse=True))
        if top_n:
            ranked = dict(list(ranked.items())[:top_n])
        return {k: round(v, 6) for k, v in ranked.items()}

    def criticality(self, part_id: str, demand_by_part: dict[str, float] | None = None) -> dict:
        """Composite criticality: reach upstream + shared usage + demand exposure."""
        parents = self.reverse_dependencies(part_id)
        direct_parents = list(self.g.predecessors(part_id)) if part_id in self.g else []
        demand = demand_by_part or {}
        exposed = sum(demand.get(p, 0.0) for p in [*parents, part_id])
        return {
            "part_id": part_id,
            "affected_assemblies": len(parents),
            "direct_parent_count": len(direct_parents),
            "demand_quantity_exposed": exposed,
            "criticality_score": round(
                len(parents) * 1.0 + len(direct_parents) * 0.5 + exposed / 100.0, 4
            ),
        }

    def supplier_concentration(self, part_id: str, supplier_parts: pd.DataFrame) -> dict:
        """Single-source risk across the part's downstream component tree."""
        comps = [*self.dependencies(part_id), part_id]
        sp = supplier_parts[supplier_parts["part_id"].isin(comps)]
        counts = sp.groupby("part_id")["supplier_id"].nunique()
        single = counts[counts == 1]
        return {
            "components_in_tree": len(comps),
            "components_with_suppliers": int(counts.shape[0]),
            "single_source_components": int(single.shape[0]),
            "single_source_ratio": round(float(single.shape[0]) / counts.shape[0], 4)
            if counts.shape[0]
            else 0.0,
        }
