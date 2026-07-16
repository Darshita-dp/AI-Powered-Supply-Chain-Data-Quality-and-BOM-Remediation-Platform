"""Rule and issue domain models."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class RuleDomain(StrEnum):
    COMPLETENESS = "completeness"
    UNIQUENESS = "uniqueness"
    VALIDITY = "validity"
    REFERENTIAL = "referential_integrity"
    CONSISTENCY = "cross_field_consistency"
    TEMPORAL = "temporal_consistency"
    ANOMALY = "anomaly"
    GRAPH = "graph_integrity"
    RECONCILIATION = "document_reconciliation"


class RuleSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Rule(BaseModel):
    """A registered data-quality rule.

    `sql` must return one row per violation with columns:
        entity_type, entity_key, field, failed_value, evidence
    (missing columns are filled with NULL by the engine's wrapper).
    """

    rule_id: str
    name: str
    description: str
    domain: RuleDomain
    severity: RuleSeverity
    rule_type: str = "sql"
    owner_role: str = "data_steward"
    threshold: float | None = None
    enabled: bool = True
    version: int = 1
    sql: str
    effective_date: date = date(2026, 7, 1)
    remediation_guidance: str = Field(default="Review evidence and correct at source.")
