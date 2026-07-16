"""Application settings loaded from environment variables / .env.

All settings use the BOMG_ prefix (see .env.example). Snowflake and hosted AI
credentials are optional: the platform defaults to a fully local configuration.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class WarehouseBackend(StrEnum):
    DUCKDB = "duckdb"
    SNOWFLAKE = "snowflake"


class AIProviderKind(StrEnum):
    MOCK = "mock"
    SNOWFLAKE_CORTEX = "snowflake_cortex"
    ANTHROPIC = "anthropic"


class DataProfile(StrEnum):
    SMOKE = "smoke"
    DEMO = "demo"
    FULL = "full"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BOMG_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    env: str = "local"
    log_level: str = "INFO"

    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173"

    warehouse_backend: WarehouseBackend = WarehouseBackend.DUCKDB
    duckdb_path: Path = Path("warehouse/local/bom_guardian.duckdb")

    ai_provider: AIProviderKind = AIProviderKind.MOCK
    ai_call_budget: int = 200
    ai_timeout_seconds: int = 30

    data_profile: DataProfile = DataProfile.SMOKE
    random_seed: int = 20260716

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
