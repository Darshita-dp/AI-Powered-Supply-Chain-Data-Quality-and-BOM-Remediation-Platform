"""Transparent quality scoring at record/entity, BOM, and enterprise level.

Scores are 0-100. Weights are explicit module constants so the method is fully
inspectable; issues subtract weight by severity, scaled by domain relevance.
"""

from __future__ import annotations

import pandas as pd

from bom_guardian.observability import get_logger
from bom_guardian.warehouse import LocalWarehouse

SEVERITY_PENALTY: dict[str, float] = {
    "critical": 25.0,
    "high": 12.0,
    "medium": 5.0,
    "low": 2.0,
}

# Source reliability (mirrors data_generator.reference.SOURCE_SYSTEMS)
SOURCE_RELIABILITY: dict[str, float] = {
    "SAP_ECC": 0.92,
    "ORACLE_EBS": 0.85,
    "LEGACY_MFG": 0.65,
    "PLM_TEAMCENTER": 0.88,
    "SUPPLIER_PORTAL": 0.72,
}

ENTERPRISE_SEVERITY_WEIGHT: dict[str, float] = {
    "critical": 8.0,
    "high": 4.0,
    "medium": 1.5,
    "low": 0.5,
}


class QualityScorer:
    """Computes and persists quality scores from open issues."""

    def __init__(self, warehouse: LocalWarehouse) -> None:
        self.wh = warehouse
        self._log = get_logger("quality_scorer")

    def score_entities(self) -> pd.DataFrame:
        """Per-entity score: 100 minus severity penalties, floored at 0,
        adjusted by source reliability for part entities."""
        issues = self.wh.query(
            "SELECT entity_type, entity_key, severity, COUNT(*) AS n "
            "FROM quality.dq_issues WHERE status != 'CLOSED' GROUP BY 1, 2, 3"
        )
        penalties = (
            issues.assign(
                penalty=lambda d: d["severity"].map(SEVERITY_PENALTY).fillna(2.0) * d["n"]
            )
            .groupby(["entity_type", "entity_key"], as_index=False)["penalty"]
            .sum()
        )
        penalties["quality_score"] = (100.0 - penalties["penalty"]).clip(lower=0.0)

        # blend part scores with source reliability (reliability shifts up to 10 pts)
        parts = self.wh.query("SELECT part_key, source_system FROM core.dim_part")
        parts["reliability"] = parts["source_system"].map(SOURCE_RELIABILITY).fillna(0.7)
        merged = penalties.merge(parts, left_on="entity_key", right_on="part_key", how="left")
        is_part = merged["entity_type"] == "part"
        merged.loc[is_part, "quality_score"] = (
            merged.loc[is_part, "quality_score"] * 0.9
            + merged.loc[is_part, "reliability"].fillna(0.7) * 10.0
        ).clip(0.0, 100.0)

        out = merged[["entity_type", "entity_key", "penalty", "quality_score"]].round(2)
        self.wh.load_dataframe("quality", "entity_scores", out)
        return out

    def score_boms(self) -> pd.DataFrame:
        """Per-assembly BOM score from issues attached to its relationships."""
        rels = self.wh.query("SELECT bom_rel_key, parent_part_key FROM core.fact_bom_relationship")
        issues = self.wh.query(
            "SELECT entity_key, severity FROM quality.dq_issues "
            "WHERE entity_type = 'bom_relationship' AND status != 'CLOSED'"
        )
        issues["penalty"] = issues["severity"].map(SEVERITY_PENALTY).fillna(2.0)
        merged = rels.merge(issues, left_on="bom_rel_key", right_on="entity_key", how="left")
        agg = merged.groupby("parent_part_key", as_index=False)["penalty"].sum()
        agg["bom_quality_score"] = (100.0 - agg["penalty"].fillna(0.0)).clip(lower=0.0).round(2)
        self.wh.load_dataframe("quality", "bom_scores", agg)
        return agg

    def enterprise_score(self) -> dict:
        """Business-weighted enterprise score: issues weighted by severity and
        normalized by entity volume, not a raw issue count."""
        issues = self.wh.query(
            "SELECT severity, COUNT(*) AS n FROM quality.dq_issues "
            "WHERE status != 'CLOSED' GROUP BY 1"
        )
        entities = self.wh.query("SELECT COUNT(*) AS n FROM core.dim_part").iloc[0]["n"]
        weighted = float(
            (issues["severity"].map(ENTERPRISE_SEVERITY_WEIGHT).fillna(0.5) * issues["n"]).sum()
        )
        # 1 weighted point per part would zero the score
        score = max(0.0, 100.0 - (weighted / max(int(entities), 1)) * 100.0 / 8.0)
        result = {
            "enterprise_quality_score": round(score, 2),
            "weighted_issue_points": round(weighted, 1),
            "open_issues": int(issues["n"].sum()) if not issues.empty else 0,
            "parts_in_scope": int(entities),
        }
        self.wh.load_dataframe("quality", "enterprise_score", pd.DataFrame([result]))
        self._log.info("enterprise_score", **result)
        return result

    def run_all(self) -> dict:
        entity = self.score_entities()
        boms = self.score_boms()
        ent = self.enterprise_score()
        return {"entities_scored": len(entity), "boms_scored": len(boms), **ent}
