"""Unit tests for configuration loading."""

from bom_guardian.config.settings import (
    AIProviderKind,
    DataProfile,
    Settings,
    WarehouseBackend,
)


def test_defaults_are_fully_local() -> None:
    s = Settings(_env_file=None)
    assert s.warehouse_backend is WarehouseBackend.DUCKDB
    assert s.ai_provider is AIProviderKind.MOCK
    assert s.data_profile is DataProfile.SMOKE


def test_env_override(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("BOMG_DATA_PROFILE", "demo")
    monkeypatch.setenv("BOMG_RANDOM_SEED", "42")
    s = Settings(_env_file=None)
    assert s.data_profile is DataProfile.DEMO
    assert s.random_seed == 42


def test_cors_origin_list_parses_csv() -> None:
    s = Settings(_env_file=None, cors_origins="http://a.test, http://b.test")
    assert s.cors_origin_list == ["http://a.test", "http://b.test"]
