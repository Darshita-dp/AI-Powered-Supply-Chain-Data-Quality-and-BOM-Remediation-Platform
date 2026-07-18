"""Tests for the optional Anthropic AI provider.

Unit tests inject a fake Anthropic client (no network, no key). A single integration
test runs the real SDK only when ANTHROPIC_API_KEY is set — otherwise it skips cleanly.
"""

from __future__ import annotations

import json
import os

import pytest

from bom_guardian.ai import (
    AnthropicAIProvider,
    EvidenceBundle,
    RemediationEngine,
    RemediationProposal,
)
from bom_guardian.ai.schemas import EvidenceItem, validate_grounding


class _Block:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _Usage:
    input_tokens = 1234
    output_tokens = 210


class _Response:
    def __init__(self, text: str, stop_reason: str = "end_turn") -> None:
        self.content = [_Block(text)]
        self.usage = _Usage()
        self.stop_reason = stop_reason


class FakeMessages:
    def __init__(self, response: _Response | Exception) -> None:
        self._response = response
        self.calls: list[dict] = []

    def create(self, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append(kwargs)
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


class FakeAnthropic:
    def __init__(self, response: _Response | Exception) -> None:
        self.messages = FakeMessages(response)


def _bundle() -> EvidenceBundle:
    return EvidenceBundle(
        issue_id="ISS-1",
        issue_summary="invalid unit of measure",
        items=[
            EvidenceItem(evidence_id=f"EVD-{i}", kind="rule_violation", summary=f"e{i}")
            for i in range(1, 3)
        ],
    )


def _proposal_text() -> str:
    return json.dumps(
        {
            "issue_id": "ISS-1",
            "recommended_action": "correct_field",
            "evidence_refs": ["EVD-1", "EVD-2"],
            "confidence": 0.7,
            "human_review_required": True,
            "explanation": "grounded in [EVD-1] and [EVD-2]",
        }
    )


def test_provider_parses_structured_output() -> None:
    provider = AnthropicAIProvider(
        client=FakeAnthropic(_Response(_proposal_text())), model="claude-opus-4-8"
    )
    out = provider.propose("system", _bundle())
    assert out["recommended_action"] == "correct_field"
    assert out["provider"] == "anthropic"
    assert out["model"] == "claude-opus-4-8"
    assert provider.last_usage["output_tokens"] == 210
    assert provider.last_usage["latency_ms"] >= 0


def test_provider_requests_json_schema_and_delimits_evidence() -> None:
    fake = FakeAnthropic(_Response(_proposal_text()))
    AnthropicAIProvider(client=fake).propose("sys", _bundle())
    call = fake.messages.calls[0]
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert "<untrusted_evidence>" in call["messages"][0]["content"]
    assert call["max_tokens"] > 0


def test_provider_output_passes_engine_validation() -> None:
    provider = AnthropicAIProvider(client=FakeAnthropic(_Response(_proposal_text())))
    engine = RemediationEngine(provider)
    bundle = _bundle()
    proposal = engine.propose(bundle)
    assert isinstance(proposal, RemediationProposal)
    assert validate_grounding(proposal, bundle) == []


def test_provider_surfaces_api_errors() -> None:
    provider = AnthropicAIProvider(client=FakeAnthropic(RuntimeError("boom")))
    with pytest.raises(RuntimeError, match="Anthropic API call failed"):
        provider.propose("sys", _bundle())


def test_provider_rejects_non_json() -> None:
    provider = AnthropicAIProvider(client=FakeAnthropic(_Response("not json")))
    with pytest.raises(ValueError, match="non-JSON"):
        provider.propose("sys", _bundle())


def test_provider_handles_refusal() -> None:
    provider = AnthropicAIProvider(client=FakeAnthropic(_Response("{}", stop_reason="refusal")))
    with pytest.raises(ValueError, match="refused"):
        provider.propose("sys", _bundle())


def test_provider_requires_config_when_no_client() -> None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY is set; the unconfigured path cannot be exercised")
    # Without an injected client, the provider must refuse clearly — either because the
    # SDK isn't installed or because no key is configured. Both are valid pending states.
    with pytest.raises(RuntimeError, match=r"(ANTHROPIC_API_KEY is not set|not installed)"):
        AnthropicAIProvider().propose("sys", _bundle())


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set — real Anthropic validation is external/pending",
)
def test_real_anthropic_provider_end_to_end() -> None:
    provider = AnthropicAIProvider()
    engine = RemediationEngine(provider)
    proposal = engine.propose(_bundle())
    assert proposal.human_review_required is True
    assert proposal.evidence_refs
    assert provider.last_usage.get("output_tokens")
