"""API response/request models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


class PartOut(BaseModel):
    part_key: str
    source_part_number: str | None = None
    source_system: str | None = None
    description: str | None = None
    category: str | None = None
    uom: str | None = None
    lifecycle_status: str | None = None
    procurement_type: str | None = None
    standard_cost: float | None = None
    lead_time_days: int | None = None
    primary_plant: str | None = None


class IssueOut(BaseModel):
    issue_id: str
    rule_id: str
    entity_type: str
    entity_key: str
    field: str | None = None
    severity: str
    domain: str
    status: str
    detected_at: str | None = None


class EvidenceOut(BaseModel):
    evidence_id: str
    issue_id: str
    field: str | None = None
    failed_value: str | None = None


class DecisionIn(BaseModel):
    reviewer: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=2000)


class MergeScenarioIn(BaseModel):
    duplicate_id: str
    surviving_id: str


class FieldCorrectionIn(BaseModel):
    part_id: str
    field: str
    new_value: str


class ComponentReplacementIn(BaseModel):
    parent_id: str
    old_child_id: str
    new_child_id: str


class ApiError(BaseModel):
    error: str
    detail: Any | None = None
    correlation_id: str | None = None
