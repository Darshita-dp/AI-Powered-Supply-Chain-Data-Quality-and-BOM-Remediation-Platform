"""Strict schemas for AI remediation proposals and their evidence.

The proposal schema is the ONLY output contract an AI provider can fulfill.
There is deliberately no action that approves, applies, or mutates anything:
proposals enter the human-review workflow and stop there.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

PROMPT_VERSION = "1.0"


class RecommendedAction(StrEnum):
    MERGE_RECORDS = "merge_records"
    CORRECT_FIELD = "correct_field"
    REPLACE_COMPONENT = "replace_component"
    DEACTIVATE_RECORD = "deactivate_record"
    UPDATE_RELATIONSHIP = "update_relationship"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"  # abstention


class FieldLevelDecision(BaseModel):
    field: str
    current_value: str | None = None
    proposed_value: str | None = None
    source_of_truth: str | None = None
    evidence_ref: str


class EvidenceItem(BaseModel):
    evidence_id: str
    kind: str  # rule_violation | match_feature | graph_result | impact | source_policy
    summary: str
    detail: dict = Field(default_factory=dict)


class EvidenceBundle(BaseModel):
    """Everything the AI may ground its proposal in — nothing else."""

    issue_id: str
    issue_summary: str
    items: list[EvidenceItem]

    @property
    def ids(self) -> set[str]:
        return {i.evidence_id for i in self.items}


class RemediationProposal(BaseModel):
    issue_id: str
    recommended_action: RecommendedAction
    surviving_record: str | None = None
    records_affected: list[str] = Field(default_factory=list)
    field_decisions: list[FieldLevelDecision] = Field(default_factory=list)
    evidence_refs: list[str] = Field(min_length=1)
    rules_resolved: list[str] = Field(default_factory=list)
    rules_unresolved: list[str] = Field(default_factory=list)
    business_impact_summary: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    risks: list[str] = Field(default_factory=list)
    human_review_required: bool = True
    explanation: str
    provider: str
    model: str
    prompt_version: str = PROMPT_VERSION
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    @field_validator("human_review_required")
    @classmethod
    def review_always_required(cls, v: bool) -> bool:
        # governance invariant: no AI proposal may opt out of human review
        if not v:
            raise ValueError("AI proposals cannot waive human review")
        return v


def validate_grounding(proposal: RemediationProposal, bundle: EvidenceBundle) -> list[str]:
    """Return grounding violations: refs to evidence that was never provided."""
    problems = []
    unknown = set(proposal.evidence_refs) - bundle.ids
    if unknown:
        problems.append(f"unknown evidence refs: {sorted(unknown)}")
    for fd in proposal.field_decisions:
        if fd.evidence_ref not in bundle.ids:
            problems.append(f"field decision '{fd.field}' cites unknown evidence {fd.evidence_ref}")
    if proposal.issue_id != bundle.issue_id:
        problems.append("proposal issue_id does not match evidence bundle")
    return problems
