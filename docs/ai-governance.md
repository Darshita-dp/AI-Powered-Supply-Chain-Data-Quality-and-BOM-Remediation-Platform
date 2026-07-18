# AI Governance Statement — BOM Guardian AI

## Where AI is (and is not) used

| Capability | AI used? | Rationale |
|---|---|---|
| Data-quality rule detection | No — deterministic SQL | Rules must be reproducible and auditable |
| Entity resolution | Interpretable ML (LR / gradient boosting) over explicit features | Explainable evidence beats opaque embeddings for steward trust |
| Golden-record survivorship | No — weighted deterministic policy | Master data selection must be explainable and reversible |
| Document extraction | Deterministic first; AI reserved for ambiguous fields | Structured fields need no model |
| Remediation proposals | Yes — via governed provider interface | Drafting structured proposals is where generation adds value |
| Copilot | Deterministic classification + allowlisted retrieval | Read-only Q&A grounded in real records |

## Hard guarantees

1. **No AI path can mutate data.** Providers return dicts; the engine validates and
   returns proposals; only the human decision endpoints change issue state — and the
   proposal schema contains no approve action, and `human_review_required` cannot be
   set false (schema-enforced, tested). Those decision endpoints require a **data steward
   or administrator** role, and the reviewer recorded on each decision is the
   authenticated principal, never a name supplied in the request body (demonstration
   auth; see `docs/security-model.md`).
2. **Grounding is enforced**, not requested: evidence references outside the supplied
   bundle cause rejection of the proposal (tested).
3. **Abstention is a first-class outcome** (`insufficient_evidence`), triggered on
   sparse evidence (tested).
4. **Every AI call is audited** to `quality.ai_call_audit`: provider, model, prompt
   version, input/output sizes, latency, validation result, abstention, confidence.
   Surfaced in the AI Governance UI page and mart.
5. **Untrusted content stays untrusted**: system instructions and evidence are passed
   separately; document text instructions are flagged and never followed (tested).

## Providers

| Provider | Status |
|---|---|
| `DeterministicMockAIProvider` | Implemented and tested — default for all local runs and CI |
| `SnowflakeCortexAIProvider` | Implemented locally on Cortex **`AI_COMPLETE`** (the legacy `SNOWFLAKE.CORTEX.COMPLETE` was replaced) with a response schema, JSON validation, error handling, env-configurable model, and latency capture; fake-connection tested. External validation pending (no Snowflake credentials); raises a clear error rather than pretending |
| `AnthropicAIProvider` | Implemented on the official Anthropic SDK: `output_config.format` JSON-schema constraint, JSON parse + shape check before the engine's full validation, SDK retry/timeout, refusal handling, token + latency capture, env-configured key (`ANTHROPIC_API_KEY`) and model (`BOMG_ANTHROPIC_MODEL`, default `claude-opus-4-8`); fake-client tested. **External validation pending** until `scripts/validate_real_ai_provider.py` is run with a real key (it skips cleanly without one — no fabricated artifact) |

## Feedback loop policy

Reviewer decisions are recorded and reported (acceptance/override rates). Feedback is
**never** used for automatic retraining; retraining is a manual, evaluated workflow
against ground truth.
