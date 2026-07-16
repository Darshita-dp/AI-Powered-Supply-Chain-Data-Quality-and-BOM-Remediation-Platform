"""AI remediation engine tests: schema, grounding, abstention, audit, governance."""

import pytest
from pydantic import ValidationError

from bom_guardian.ai import (
    DeterministicMockAIProvider,
    EvidenceBundle,
    RemediationEngine,
    RemediationProposal,
    SnowflakeCortexAIProvider,
)
from bom_guardian.ai.schemas import EvidenceItem, validate_grounding
from bom_guardian.warehouse import LocalWarehouse


def _bundle(n_items: int = 3, issue_id: str = "ISS-1") -> EvidenceBundle:
    return EvidenceBundle(
        issue_id=issue_id,
        issue_summary="duplicate part records detected across source systems",
        items=[
            EvidenceItem(
                evidence_id=f"EVD-{i}",
                kind="rule_violation",
                summary=f"evidence item {i}",
                detail={"record_id": f"PRT{i:03d}"},
            )
            for i in range(1, n_items + 1)
        ],
    )


def test_mock_provider_produces_schema_valid_proposal() -> None:
    raw = DeterministicMockAIProvider().propose("sys", _bundle())
    proposal = RemediationProposal.model_validate(raw)
    assert proposal.recommended_action.value == "merge_records"
    assert proposal.human_review_required is True
    assert proposal.evidence_refs


def test_grounded_explanation_cites_provided_evidence() -> None:
    bundle = _bundle()
    proposal = RemediationProposal.model_validate(
        DeterministicMockAIProvider().propose("sys", bundle)
    )
    assert validate_grounding(proposal, bundle) == []
    assert "[EVD-1]" in proposal.explanation


def test_abstention_on_sparse_evidence() -> None:
    raw = DeterministicMockAIProvider().propose("sys", _bundle(n_items=1))
    proposal = RemediationProposal.model_validate(raw)
    assert proposal.recommended_action.value == "insufficient_evidence"
    assert proposal.confidence <= 0.3


def test_proposals_cannot_waive_human_review() -> None:
    raw = DeterministicMockAIProvider().propose("sys", _bundle())
    raw["human_review_required"] = False
    with pytest.raises(ValidationError):
        RemediationProposal.model_validate(raw)


def test_no_approve_action_exists() -> None:
    from bom_guardian.ai.schemas import RecommendedAction

    assert not any("approve" in a.value for a in RecommendedAction)


def test_grounding_validation_rejects_unknown_refs() -> None:
    bundle = _bundle()
    raw = DeterministicMockAIProvider().propose("sys", bundle)
    raw["evidence_refs"] = ["EVD-1", "EVD-FABRICATED"]
    proposal = RemediationProposal.model_validate(raw)
    problems = validate_grounding(proposal, bundle)
    assert problems and "EVD-FABRICATED" in problems[0]


def test_engine_rejects_ungrounded_output() -> None:
    class LyingProvider(DeterministicMockAIProvider):
        def propose(self, system_instructions, bundle):  # type: ignore[no-untyped-def]
            raw = super().propose(system_instructions, bundle)
            raw["evidence_refs"] = ["EVD-HALLUCINATED"]
            return raw

    engine = RemediationEngine(LyingProvider())
    with pytest.raises(ValueError, match="grounding"):
        engine.propose(_bundle())


def test_cortex_provider_requires_credentials() -> None:
    with pytest.raises(RuntimeError, match="pending"):
        SnowflakeCortexAIProvider().propose("sys", _bundle())


def test_engine_audits_calls_in_warehouse() -> None:
    with LocalWarehouse(":memory:") as wh:
        engine = RemediationEngine(DeterministicMockAIProvider(), warehouse=wh)
        engine.propose(_bundle())
        audit = wh.query("SELECT * FROM quality.ai_call_audit")
        assert len(audit) == 1
        row = audit.iloc[0]
        assert row["provider"] == "mock"
        assert row["validation_result"] == "valid"
        assert row["latency_ms"] >= 0


def test_end_to_end_evidence_gathering_from_quality_tables() -> None:
    with LocalWarehouse(":memory:") as wh:
        import pandas as pd

        wh.execute(
            "CREATE TABLE quality.dq_issues (issue_id VARCHAR, rule_id VARCHAR, "
            "execution_id VARCHAR, run_id VARCHAR, entity_type VARCHAR, "
            "entity_key VARCHAR, field VARCHAR, severity VARCHAR, domain VARCHAR, "
            "status VARCHAR, detected_at TIMESTAMP)"
        )
        wh.execute(
            "INSERT INTO quality.dq_issues VALUES ('ISS-9', 'VALD-001', 'E1', 'R1', "
            "'part', 'PRT000123', 'uom', 'high', 'validity', 'DETECTED', now())"
        )
        wh.load_dataframe(
            "quality",
            "dq_rules",
            pd.DataFrame(
                [
                    {
                        "rule_id": "VALD-001",
                        "name": "Invalid UOM code",
                        "remediation_guidance": "Correct the UOM against the governed list.",
                    }
                ]
            ),
        )
        wh.load_dataframe(
            "quality",
            "dq_issue_evidence",
            pd.DataFrame(
                [
                    {
                        "evidence_id": "EVD-A",
                        "issue_id": "ISS-9",
                        "field": "uom",
                        "failed_value": "PCS",
                        "rule_sql_version": 1,
                        "detected_at": None,
                    }
                ]
            ),
        )
        engine = RemediationEngine(DeterministicMockAIProvider(), warehouse=wh)
        bundle = engine.gather_evidence("ISS-9")
        assert bundle.issue_id == "ISS-9"
        assert len(bundle.items) == 2  # violation evidence + rule policy
        proposal = engine.propose(bundle)
        assert proposal.recommended_action.value == "correct_field"
