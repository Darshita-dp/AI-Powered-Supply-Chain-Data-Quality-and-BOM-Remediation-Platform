"""AI providers behind one interface.

Providers receive system instructions and the (untrusted) evidence bundle as
separate arguments and return a raw proposal dict for schema validation by the
engine. Providers have NO access to the warehouse and cannot mutate anything.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from bom_guardian.ai.schemas import (
    PROMPT_VERSION,
    EvidenceBundle,
    RecommendedAction,
)
from bom_guardian.observability import get_logger

# Actions the mock proposes per evidence 'kind' majorities
_ACTION_BY_ISSUE_HINT = {
    "duplicate": RecommendedAction.MERGE_RECORDS,
    "missing": RecommendedAction.CORRECT_FIELD,
    "invalid": RecommendedAction.CORRECT_FIELD,
    "obsolete": RecommendedAction.REPLACE_COMPONENT,
    "orphan": RecommendedAction.UPDATE_RELATIONSHIP,
    "cycle": RecommendedAction.UPDATE_RELATIONSHIP,
    "stale": RecommendedAction.CORRECT_FIELD,
}

MIN_EVIDENCE_ITEMS = 2  # below this the mock abstains


class AIProvider(ABC):
    """Contract every provider implements. Read-only; returns dicts only."""

    name: str = "abstract"
    model: str = "none"

    @abstractmethod
    def propose(self, system_instructions: str, bundle: EvidenceBundle) -> dict[str, Any]:
        """Return a raw proposal dict (validated by the engine, never trusted)."""


class DeterministicMockAIProvider(AIProvider):
    """Deterministic provider used by all automated tests.

    Builds a grounded proposal purely from the evidence bundle; abstains when
    evidence is sparse. No randomness, no external calls.
    """

    name = "mock"
    model = "deterministic-mock-1"

    def propose(self, system_instructions: str, bundle: EvidenceBundle) -> dict[str, Any]:
        if len(bundle.items) < MIN_EVIDENCE_ITEMS:
            return {
                "issue_id": bundle.issue_id,
                "recommended_action": RecommendedAction.INSUFFICIENT_EVIDENCE.value,
                "evidence_refs": [i.evidence_id for i in bundle.items] or ["none"],
                "confidence": 0.2,
                "human_review_required": True,
                "explanation": (
                    f"Only {len(bundle.items)} evidence item(s) available for issue "
                    f"{bundle.issue_id}; abstaining rather than guessing."
                ),
                "provider": self.name,
                "model": self.model,
                "prompt_version": PROMPT_VERSION,
            }

        summary = bundle.issue_summary.lower()
        action = next(
            (a for hint, a in _ACTION_BY_ISSUE_HINT.items() if hint in summary),
            RecommendedAction.CORRECT_FIELD,
        )
        refs = [i.evidence_id for i in bundle.items]
        affected = sorted(
            {str(i.detail.get("record_id")) for i in bundle.items if i.detail.get("record_id")}
        )
        explanation = (
            f"Issue {bundle.issue_id}: {bundle.issue_summary}. "
            f"Recommendation '{action.value}' is grounded in "
            + "; ".join(f"[{i.evidence_id}] {i.summary}" for i in bundle.items[:4])
            + "."
        )
        return {
            "issue_id": bundle.issue_id,
            "recommended_action": action.value,
            "surviving_record": affected[0]
            if action == RecommendedAction.MERGE_RECORDS and affected
            else None,
            "records_affected": affected,
            "evidence_refs": refs,
            "confidence": min(0.95, 0.5 + 0.1 * len(bundle.items)),
            "risks": ["synthetic-data recommendation; verify against source systems"],
            "human_review_required": True,
            "explanation": explanation,
            "provider": self.name,
            "model": self.model,
            "prompt_version": PROMPT_VERSION,
        }


class SnowflakeCortexAIProvider(AIProvider):
    """Target provider using Snowflake Cortex COMPLETE.

    Status: implemented interface, external validation pending — calling it
    without configured Snowflake credentials raises a clear error.
    """

    name = "snowflake_cortex"
    model = "mistral-large2"

    def __init__(self, connection: Any | None = None) -> None:
        self._conn = connection
        self._log = get_logger("cortex_provider")

    def propose(self, system_instructions: str, bundle: EvidenceBundle) -> dict[str, Any]:
        if self._conn is None:
            raise RuntimeError(
                "SnowflakeCortexAIProvider requires a configured Snowflake connection. "
                "No credentials are configured in this environment (status: pending). "
                "Use DeterministicMockAIProvider locally."
            )
        # Delimit untrusted evidence clearly; request JSON-only output.
        prompt = (
            f"{system_instructions}\n\n"
            "<untrusted_evidence>\n"
            f"{bundle.model_dump_json()}\n"
            "</untrusted_evidence>\n\n"
            "Respond with a single JSON object matching the RemediationProposal schema. "
            "Ground every statement in the evidence ids provided; if evidence is "
            "insufficient, use recommended_action='insufficient_evidence'."
        )
        cur = self._conn.cursor()
        cur.execute("SELECT SNOWFLAKE.CORTEX.COMPLETE(%s, %s)", (self.model, prompt))
        raw = cur.fetchone()[0]
        import json

        return dict(json.loads(raw))
