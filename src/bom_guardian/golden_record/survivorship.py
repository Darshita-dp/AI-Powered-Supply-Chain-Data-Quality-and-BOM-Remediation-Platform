"""Field-level golden-record survivorship.

Never selects one whole source row. Each governed field is scored per source
record on completeness, source reliability, recency, and cross-source
agreement; the best value survives with a full audit trail (source, reason,
confidence, alternatives). Recommendations are reversible: every alternative
value and its source are retained, and nothing here mutates warehouse state.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import UTC, date, datetime

import pandas as pd

from bom_guardian.observability import get_logger

SURVIVORSHIP_VERSION = "1.0"

# Mirrors data_generator.reference.SOURCE_SYSTEMS reliability
SOURCE_RELIABILITY: dict[str, float] = {
    "SAP_ECC": 0.92,
    "ORACLE_EBS": 0.85,
    "LEGACY_MFG": 0.65,
    "PLM_TEAMCENTER": 0.88,
    "SUPPLIER_PORTAL": 0.72,
}

# Score weights (documented, configurable via constructor)
DEFAULT_WEIGHTS = {"reliability": 0.45, "recency": 0.25, "agreement": 0.30}

# Domain policy: fields where a specific source domain is preferred, expressed
# as a reliability bonus for that source when it has a value.
FIELD_SOURCE_PREFERENCE: dict[str, dict[str, float]] = {
    "description": {"PLM_TEAMCENTER": 0.10},  # engineering owns descriptions
    "standard_cost": {"SAP_ECC": 0.10, "ORACLE_EBS": 0.05},  # finance/ERP owns cost
    "lead_time_days": {"SUPPLIER_PORTAL": 0.25},  # supplier data owns lead time
    "uom": {"SAP_ECC": 0.05},  # governed reference data in ERP
}

GOVERNED_FIELDS: list[str] = [
    "source_part_number",
    "description",
    "category",
    "uom",
    "lifecycle_status",
    "manufacturer_part_number",
    "standard_cost",
    "lead_time_days",
    "primary_plant",
]


@dataclass
class Alternative:
    value: object
    source_record: str
    source_system: str
    score: float


@dataclass
class FieldDecision:
    field: str
    selected_value: object
    source_record: str
    source_system: str
    reason: str
    confidence: float
    selected_at: str
    version: str = SURVIVORSHIP_VERSION
    alternatives: list[Alternative] = dc_field(default_factory=list)


@dataclass
class GoldenRecord:
    entity_id: str
    member_record_ids: list[str]
    fields: dict[str, FieldDecision]
    created_at: str

    def as_flat_dict(self) -> dict:
        return {name: d.selected_value for name, d in self.fields.items()}


class GoldenRecordBuilder:
    """Builds a golden record from a cluster of source records for one entity."""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        reliability: dict[str, float] | None = None,
    ) -> None:
        self.weights = weights or DEFAULT_WEIGHTS
        self.reliability = reliability or SOURCE_RELIABILITY
        self._log = get_logger("golden_record")

    def build(self, cluster: pd.DataFrame, entity_id: str | None = None) -> GoldenRecord:
        """cluster: rows of part_master records believed to be the same entity."""
        if cluster.empty:
            raise ValueError("Cannot build a golden record from an empty cluster")
        entity = entity_id or f"GLD-{cluster.iloc[0]['part_id']}"
        now = datetime.now(UTC).isoformat()
        decisions: dict[str, FieldDecision] = {}
        for fld in GOVERNED_FIELDS:
            if fld not in cluster.columns:
                continue
            decision = self._decide_field(cluster, fld, now)
            if decision is not None:
                decisions[fld] = decision
        self._log.info(
            "golden_record_built",
            entity_id=entity,
            members=len(cluster),
            fields=len(decisions),
        )
        return GoldenRecord(
            entity_id=entity,
            member_record_ids=cluster["part_id"].tolist(),
            fields=decisions,
            created_at=now,
        )

    # ------------------------------------------------------------------
    def _decide_field(self, cluster: pd.DataFrame, fld: str, now: str) -> FieldDecision | None:
        candidates: list[Alternative] = []
        values_seen: list[object] = []
        for _, row in cluster.iterrows():
            value = row.get(fld)
            if value is None or (isinstance(value, float) and pd.isna(value)) or value == "":
                continue
            values_seen.append(value)
        if not values_seen:
            return None

        # cross-source agreement: share of non-null records carrying this value
        agreement = {v: values_seen.count(v) / len(values_seen) for v in set(map(str, values_seen))}

        max_recency = self._max_recency(cluster)
        for _, row in cluster.iterrows():
            value = row.get(fld)
            if value is None or (isinstance(value, float) and pd.isna(value)) or value == "":
                continue
            src = str(row.get("source_system") or "")
            rel = self.reliability.get(src, 0.6)
            rel += FIELD_SOURCE_PREFERENCE.get(fld, {}).get(src, 0.0)
            rec = self._recency_score(row.get("last_updated"), max_recency)
            agr = agreement.get(str(value), 0.0)
            score = (
                self.weights["reliability"] * rel
                + self.weights["recency"] * rec
                + self.weights["agreement"] * agr
            )
            candidates.append(
                Alternative(
                    value=value,
                    source_record=str(row["part_id"]),
                    source_system=src,
                    score=round(score, 4),
                )
            )

        candidates.sort(key=lambda c: c.score, reverse=True)
        best, rest = candidates[0], candidates[1:]
        reason_bits = [f"source_reliability({best.source_system})"]
        if agreement.get(str(best.value), 0) > 0.5:
            reason_bits.append(f"cross_source_agreement({agreement[str(best.value)]:.0%})")
        if FIELD_SOURCE_PREFERENCE.get(fld, {}).get(best.source_system):
            reason_bits.append(f"domain_preference({fld}<-{best.source_system})")
        # confidence: winner score scaled by its margin over the runner-up
        margin = best.score - rest[0].score if rest else best.score
        confidence = round(min(1.0, best.score * (0.7 + min(0.3, margin))), 4)
        return FieldDecision(
            field=fld,
            selected_value=best.value,
            source_record=best.source_record,
            source_system=best.source_system,
            reason=" + ".join(reason_bits),
            confidence=confidence,
            selected_at=now,
            alternatives=[a for a in rest if str(a.value) != str(best.value)],
        )

    @staticmethod
    def _max_recency(cluster: pd.DataFrame) -> date | None:
        if "last_updated" not in cluster.columns:
            return None
        series = pd.to_datetime(cluster["last_updated"], errors="coerce")
        return series.max()

    @staticmethod
    def _recency_score(value: object, max_recency: object) -> float:
        if value is None or max_recency is None or pd.isna(max_recency):
            return 0.5
        try:
            ts = pd.to_datetime(value)
        except (ValueError, TypeError):
            return 0.5
        if pd.isna(ts):
            return 0.5
        days_behind = (max_recency - ts).days
        return max(0.0, 1.0 - days_behind / 1460.0)  # linear decay over ~4 years
