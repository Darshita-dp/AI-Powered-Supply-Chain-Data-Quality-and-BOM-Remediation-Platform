"""Validate the real (Anthropic) AI remediation provider against a known issue.

Generates a real remediation recommendation for a fixed synthetic evidence bundle,
runs it through the governed engine (schema + grounding validation), and writes a
sanitized evaluation artifact. Requires ANTHROPIC_API_KEY; exits 2 (skip) without it —
so this never runs a real model in CI unless a key is explicitly configured.

Usage:
    ANTHROPIC_API_KEY=sk-... python scripts/validate_real_ai_provider.py

Writes evaluation/ai/real_provider_validation.json (sanitized — no evidence bodies).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))


def _known_bundle():  # type: ignore[no-untyped-def]
    from bom_guardian.ai import EvidenceBundle
    from bom_guardian.ai.schemas import EvidenceItem

    return EvidenceBundle(
        issue_id="ISS-VALIDATION-1",
        issue_summary="invalid unit of measure on a purchased part",
        items=[
            EvidenceItem(
                evidence_id="EVD-1",
                kind="rule_violation",
                summary="field 'uom' failed with value 'PCS' (not in the governed UOM list)",
                detail={"record_id": "PRT000123", "field": "uom"},
            ),
            EvidenceItem(
                evidence_id="RULE-VALD-001",
                kind="source_policy",
                summary="rule VALD-001 (Invalid UOM code): correct the UOM against the "
                "governed reference list (e.g. EA, KG, M).",
                detail={"record_id": "PRT000123", "severity": "high"},
            ),
        ],
    )


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "ANTHROPIC_API_KEY not set — skipping real-provider validation. "
            "Status: implemented; external validation pending."
        )
        return 2

    from bom_guardian.ai import AnthropicAIProvider, RemediationEngine

    provider = AnthropicAIProvider()
    engine = RemediationEngine(provider)  # no warehouse — pure provider validation
    bundle = _known_bundle()

    proposal = engine.propose(bundle)  # raises on schema/grounding failure

    artifact = {
        "generated_at": datetime.now(UTC).isoformat(),
        "provider": provider.name,
        "model": provider.model,
        "issue_id": bundle.issue_id,
        # sanitized: proposal metadata + validation outcome, NOT evidence bodies
        "recommended_action": proposal.recommended_action.value,
        "confidence": proposal.confidence,
        "human_review_required": proposal.human_review_required,
        "grounded_evidence_refs": proposal.evidence_refs,
        "explanation_chars": len(proposal.explanation),
        "usage": provider.last_usage,
        "schema_and_grounding": "valid",
    }
    out = REPO / "evaluation" / "ai" / "real_provider_validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2))
    print(f"Real provider validated. Artifact: {out}")
    print(
        f"  action={artifact['recommended_action']} confidence={artifact['confidence']} "
        f"tokens_out={provider.last_usage.get('output_tokens')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
