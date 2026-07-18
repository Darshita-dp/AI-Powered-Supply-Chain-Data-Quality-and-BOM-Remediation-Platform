"""Role-based authorization for the remediation workflow.

This is **demonstration authentication**, not an enterprise IAM integration. It
maps opaque bearer tokens to a principal (username + role) so the API can prove
out authorization semantics — least privilege, steward-gated approvals, and an
authenticated actor recorded on every decision. In a real deployment these
tokens would be replaced by OIDC/SAML-issued identities validated against a
corporate IdP; the *authorization* logic (the role checks below) is what a real
system would keep.

Design guarantees exercised by tests:

* Approve / reject / request-evidence require a ``STEWARD`` or ``ADMIN`` role.
* The actor recorded on a decision is the *authenticated* principal, never a
  name supplied in the request body (the body carries no reviewer field).
* Unauthenticated requests to protected endpoints are rejected (401); an
  authenticated principal without sufficient role is rejected (403).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import StrEnum

from fastapi import Depends, Header, HTTPException


class Role(StrEnum):
    """Least-privilege role ladder. Higher roles inherit lower-role reads."""

    ANALYST = "analyst"  # read-only: explore parts, issues, analytics, copilot
    STEWARD = "steward"  # analyst + approve/reject/request-evidence decisions
    ADMIN = "admin"  # steward + (reserved for) configuration/governance


@dataclass(frozen=True)
class Principal:
    username: str
    role: Role


# --- Demonstration credential store -----------------------------------------
# NOT production credentials. These are obviously-demo tokens so a reviewer can
# exercise each role locally. Override/extend via BOMG_DEMO_USERS (JSON object
# mapping token -> {"username": ..., "role": "analyst|steward|admin"}).
_DEFAULT_DEMO_USERS: dict[str, Principal] = {
    "demo-analyst-token": Principal("demo.analyst", Role.ANALYST),
    "demo-steward-token": Principal("demo.steward", Role.STEWARD),
    "demo-admin-token": Principal("demo.admin", Role.ADMIN),
}


def _load_demo_users() -> dict[str, Principal]:
    raw = os.environ.get("BOMG_DEMO_USERS")
    if not raw:
        return dict(_DEFAULT_DEMO_USERS)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover - config error path
        raise RuntimeError(f"BOMG_DEMO_USERS is not valid JSON: {exc}") from exc
    users: dict[str, Principal] = {}
    for token, spec in parsed.items():
        users[token] = Principal(str(spec["username"]), Role(spec["role"]))
    return users


def _principal_for_token(token: str) -> Principal | None:
    return _load_demo_users().get(token)


def get_principal(authorization: str | None = Header(default=None)) -> Principal:
    """Resolve the authenticated principal from an ``Authorization: Bearer``
    header. Raises 401 when the header is missing or the token is unknown."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authentication required (Authorization: Bearer <token>).",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1].strip()
    principal = _principal_for_token(token)
    if principal is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or unknown credential.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal


_ROLE_RANK = {Role.ANALYST: 0, Role.STEWARD: 1, Role.ADMIN: 2}


def require_role(minimum: Role):  # type: ignore[no-untyped-def]
    """Dependency factory enforcing a minimum role. Returns the principal so
    endpoints can record the authenticated actor."""

    def _dependency(principal: Principal = Depends(get_principal)) -> Principal:
        if _ROLE_RANK[principal.role] < _ROLE_RANK[minimum]:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Role '{principal.role.value}' is not permitted; "
                    f"'{minimum.value}' or higher is required."
                ),
            )
        return principal

    return _dependency
