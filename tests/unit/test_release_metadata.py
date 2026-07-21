"""Release metadata consistency tests.

Version strings live in four places (``pyproject.toml``, ``bom_guardian.__version__``,
the changelog heading, and the release notes title). These tests fail the build if any of
them drifts, so a future release cannot ship with a stale or mismatched version.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

from bom_guardian import __version__

REPO = Path(__file__).resolve().parents[2]
PYPROJECT = REPO / "pyproject.toml"
CHANGELOG = REPO / "CHANGELOG.md"
RELEASE_NOTES = REPO / "RELEASE_NOTES.md"

EXPECTED_VERSION = "0.9.0"


@pytest.fixture(scope="module")
def pyproject_version() -> str:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def test_pyproject_version_matches_package(pyproject_version: str) -> None:
    assert pyproject_version == __version__, (
        f"pyproject.toml declares {pyproject_version!r} but "
        f"bom_guardian.__version__ is {__version__!r}"
    )


def test_version_is_expected_release(pyproject_version: str) -> None:
    assert pyproject_version == EXPECTED_VERSION
    assert __version__ == EXPECTED_VERSION


def test_version_is_valid_semver() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__), f"not semver: {__version__!r}"


def test_changelog_has_matching_release_heading() -> None:
    text = CHANGELOG.read_text(encoding="utf-8")
    heading = re.search(rf"^## \[{re.escape(__version__)}\] - \d{{4}}-\d{{2}}-\d{{2}}$", text, re.M)
    assert heading, f"CHANGELOG.md has no '## [{__version__}] - YYYY-MM-DD' heading"


def test_changelog_keeps_an_unreleased_section() -> None:
    """A new release must leave an Unreleased section for subsequent work."""
    text = CHANGELOG.read_text(encoding="utf-8")
    assert re.search(r"^## \[Unreleased\]$", text, re.M), "CHANGELOG.md lost its Unreleased section"


def test_release_notes_name_the_release() -> None:
    text = RELEASE_NOTES.read_text(encoding="utf-8")
    assert re.search(rf"^# BOM Guardian AI v{re.escape(__version__)}$", text, re.M), (
        f"RELEASE_NOTES.md is not titled 'BOM Guardian AI v{__version__}'"
    )


def test_api_reports_the_release_version() -> None:
    """The version a client sees must match the packaged version."""
    from api.app.main import app

    assert app.version == __version__
    assert app.openapi()["info"]["version"] == __version__


def test_release_is_not_claimed_production_ready() -> None:
    """Guard the honesty rule: 0.9.x must not advertise itself as production-ready
    while external validations (Snowflake, Anthropic, Power BI) are outstanding.

    Every mention of "production-ready" must be negated (e.g. "not production-ready"),
    so an affirmative claim cannot slip in unnoticed.
    """
    notes = RELEASE_NOTES.read_text(encoding="utf-8").lower()
    for match in re.finditer(r"production[- ]ready", notes):
        preceding = re.sub(r"[*_`]", "", notes[max(0, match.start() - 30) : match.start()])
        assert "not" in preceding, (
            f"un-negated 'production-ready' claim near: {notes[match.start() - 60 : match.end()]!r}"
        )
    for pending in ("snowflake", "anthropic", "power bi"):
        assert pending in notes, f"release notes must disclose the {pending} status"
