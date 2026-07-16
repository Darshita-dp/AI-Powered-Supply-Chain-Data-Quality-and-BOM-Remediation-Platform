"""Auditable, idempotent ingestion of generated extracts into the raw layer."""

from bom_guardian.ingestion.loader import IngestionService

__all__ = ["IngestionService"]
