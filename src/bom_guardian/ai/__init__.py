"""AI provider abstraction and governed remediation proposal generation."""

from bom_guardian.ai.engine import RemediationEngine
from bom_guardian.ai.providers import (
    AIProvider,
    AnthropicAIProvider,
    DeterministicMockAIProvider,
    SnowflakeCortexAIProvider,
)
from bom_guardian.ai.schemas import EvidenceBundle, RemediationProposal


def get_ai_provider(settings=None) -> AIProvider:  # type: ignore[no-untyped-def]
    """Return the configured AI provider (BOMG_AI_PROVIDER).

    Defaults to the deterministic mock. `anthropic` requires a key; `snowflake_cortex`
    requires a Snowflake connection — both raise a clear error at call time if
    unconfigured, so tests and local runs stay on the mock.
    """
    from bom_guardian.config import AIProviderKind, get_settings

    settings = settings or get_settings()
    if settings.ai_provider is AIProviderKind.ANTHROPIC:
        return AnthropicAIProvider()
    if settings.ai_provider is AIProviderKind.SNOWFLAKE_CORTEX:
        return SnowflakeCortexAIProvider()
    return DeterministicMockAIProvider()


__all__ = [
    "AIProvider",
    "AnthropicAIProvider",
    "DeterministicMockAIProvider",
    "EvidenceBundle",
    "RemediationEngine",
    "RemediationProposal",
    "SnowflakeCortexAIProvider",
    "get_ai_provider",
]
