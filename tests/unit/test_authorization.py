"""Unit tests for the demo authorization layer (api.app.auth)."""

from __future__ import annotations

import pytest
from api.app.auth import (
    Principal,
    Role,
    get_principal,
    require_role,
)
from fastapi import HTTPException


def test_bearer_token_resolves_to_principal() -> None:
    p = get_principal("Bearer demo-steward-token")
    assert p == Principal("demo.steward", Role.STEWARD)


def test_case_insensitive_scheme() -> None:
    assert get_principal("bearer demo-admin-token").role is Role.ADMIN


@pytest.mark.parametrize("header", [None, "", "demo-steward-token", "Basic abc"])
def test_missing_or_non_bearer_header_is_401(header: str | None) -> None:
    with pytest.raises(HTTPException) as exc:
        get_principal(header)
    assert exc.value.status_code == 401


def test_unknown_token_is_401() -> None:
    with pytest.raises(HTTPException) as exc:
        get_principal("Bearer not-a-real-token")
    assert exc.value.status_code == 401


def test_require_role_allows_equal_and_higher() -> None:
    dep = require_role(Role.STEWARD)
    assert dep(Principal("s", Role.STEWARD)).role is Role.STEWARD
    assert dep(Principal("a", Role.ADMIN)).role is Role.ADMIN


def test_require_role_denies_lower_with_403() -> None:
    dep = require_role(Role.STEWARD)
    with pytest.raises(HTTPException) as exc:
        dep(Principal("an", Role.ANALYST))
    assert exc.value.status_code == 403


def test_demo_users_overridable_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "BOMG_DEMO_USERS",
        '{"tok-x": {"username": "alice", "role": "admin"}}',
    )
    assert get_principal("Bearer tok-x") == Principal("alice", Role.ADMIN)
    # The built-in demo tokens are replaced, not merged.
    with pytest.raises(HTTPException):
        get_principal("Bearer demo-steward-token")
