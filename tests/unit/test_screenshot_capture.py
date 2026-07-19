"""Smoke tests for the screenshot-capture harness (hardening H9).

These do NOT launch browsers or servers (that is the job of
`python scripts/capture_screenshots.py`). They guard the parts of the harness
that silently broke during development, so a regression fails a test run rather
than producing blank or misleading screenshots:

* the API route glob must not swallow the app's own `/src/api/*` modules,
* teardown must exist and be wired for the whole process tree,
* the committed screenshots must match the surfaces the script claims to
  capture, and each must carry alt text and a caption.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "capture_screenshots.py"
SHOTS = REPO / "docs" / "screenshots"

EXPECTED_SURFACES = {
    "command-center",
    "issue-explorer",
    "remediation-workbench",
    "part-360",
    "bom-explorer",
    "scenario-simulator",
    "ai-governance",
    "copilot",
}


@pytest.fixture(scope="module")
def module():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location("capture_screenshots", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_script_exists_and_imports(module) -> None:  # type: ignore[no-untyped-def]
    assert callable(module.capture)
    assert callable(module.main)
    assert callable(module._terminate_tree), "teardown helper must exist"


def test_api_route_glob_does_not_capture_app_modules() -> None:
    """Regression: `**/api/**` also matched /src/api/client.ts, redirecting the
    app's own source to FastAPI (404) and rendering a blank page."""
    source = SCRIPT.read_text(encoding="utf-8")
    assert 'page.route("**/api/v1/**"' in source, "route must be scoped to the API prefix"
    assert 'page.route("**/api/**"' not in source, "too-broad glob would hijack /src/api/*"


def test_ui_base_uses_localhost_not_ipv4_literal() -> None:
    """Regression: vite binds to localhost (IPv6 ::1); probing 127.0.0.1 is refused."""
    source = SCRIPT.read_text(encoding="utf-8")
    assert 'UI_BASE = f"http://localhost:{UI_PORT}"' in source


def test_teardown_kills_process_tree() -> None:
    """Regression: terminating npm left an orphaned node/vite holding the port."""
    source = SCRIPT.read_text(encoding="utf-8")
    assert "taskkill" in source and "/T" in source, "Windows teardown must kill the tree"
    assert "killpg" in source, "POSIX teardown must kill the process group"


def test_capture_is_wrapped_in_try_finally() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    # teardown must run even when capture raises
    assert "finally:" in source
    assert "_terminate_tree(proc, label)" in source


@pytest.mark.skipif(not SHOTS.exists(), reason="screenshots not captured in this checkout")
def test_committed_screenshots_cover_every_surface() -> None:
    present = {p.stem for p in SHOTS.glob("*.png")}
    missing = EXPECTED_SURFACES - present
    assert not missing, f"missing screenshots for: {sorted(missing)}"


@pytest.mark.skipif(
    not (SHOTS / "manifest.json").exists(), reason="no screenshot manifest in this checkout"
)
def test_manifest_has_alt_text_and_captions() -> None:
    manifest = json.loads((SHOTS / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["screenshots"], "manifest lists no screenshots"
    for shot in manifest["screenshots"]:
        assert (SHOTS / shot["file"]).exists(), f"{shot['file']} listed but not committed"
        assert len(shot["alt"]) > 30, f"{shot['file']} needs descriptive alt text"
        assert len(shot["caption"]) > 20, f"{shot['file']} needs a caption"


@pytest.mark.skipif(not SHOTS.exists(), reason="screenshots not captured in this checkout")
def test_screenshots_are_real_pngs_of_plausible_size() -> None:
    """A blank/failed render is tiny; guard against committing empty images."""
    for png in SHOTS.glob("*.png"):
        data = png.read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{png.name} is not a PNG"
        assert len(data) > 20_000, f"{png.name} is suspiciously small ({len(data)} bytes)"
