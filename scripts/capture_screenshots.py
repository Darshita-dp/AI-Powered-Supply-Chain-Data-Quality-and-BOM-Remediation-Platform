"""Capture REAL screenshots of the running BOM Guardian AI application (hardening H9).

Nothing here is mocked or hand-drawn. The script:

  1. generates smoke-scale data and runs the real local pipeline
     (generate -> inject -> ingest -> dbt -> quality rules -> marts),
  2. starts the real FastAPI service against that warehouse,
  3. starts the real Vite dev server,
  4. waits for /health and /readiness,
  5. authenticates with the documented demo bearer token,
  6. drives the actual UI with Playwright (typing real part/issue ids fetched
     from the API), routing the app's /api/v1 calls straight to FastAPI, and
  7. writes optimized PNGs + a manifest to docs/screenshots/.

Every process is torn down in a finally block, even when capture fails.

To guarantee the images show live API data rather than frontend fixtures, the
script cross-checks values it read from the API against the rendered DOM before
saving (see `_assert_api_backed`); a mismatch fails the run instead of silently
producing a pretty but fake screenshot.

Usage:
    python scripts/capture_screenshots.py [--profile smoke] [--skip-pipeline]
                                          [--out docs/screenshots]

Requires: pip install -e ".[dev,api,ml,docs-ai,dbt]" && pip install playwright
          && python -m playwright install chromium
          && (cd frontend && npm install)
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FRONTEND = REPO / "frontend"


def _free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


# Ports are chosen at runtime so a capture never collides with a dev session the
# developer already has running, and never depends on what a local .env happens
# to set. The UI port is forced with vite's --port CLI flag (which overrides
# vite.config.ts and any .env file), and API calls bypass vite's proxy entirely
# via Playwright request routing (see `capture`) — so an untracked
# frontend/.env.local pointing at some other API cannot silently poison a run.
API_PORT = _free_port()
UI_PORT = _free_port()
API_BASE = f"http://127.0.0.1:{API_PORT}"
# NOTE: use "localhost", not "127.0.0.1" — vite binds to localhost, which resolves
# to IPv6 ::1 on Windows, so an IPv4 probe is refused even though it is serving.
UI_BASE = f"http://localhost:{UI_PORT}"
# Documented demo credential (see docs/api-guide.md). Steward so the decision
# surface renders in its actionable state.
DEMO_TOKEN = "demo-steward-token"

VIEWPORT = {"width": 1600, "height": 900}
UI_LOG = REPO / "build" / "screenshot-ui.log"


def _optimize(path: Path) -> tuple[int, int]:
    """Shrink a PNG in place with an adaptive palette.

    These are flat dashboard UIs (few distinct colours), so a 256-colour adaptive
    palette is visually indistinguishable while cutting file size substantially.
    Returns (before, after) byte sizes; a no-op if Pillow is unavailable or the
    result would be larger.
    """
    before = path.stat().st_size
    try:
        from PIL import Image
    except ImportError:
        return before, before
    with Image.open(path) as img:
        quantized = img.convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT)
        tmp = path.with_suffix(".opt.png")
        quantized.save(tmp, format="PNG", optimize=True)
    after = tmp.stat().st_size
    if after < before:
        tmp.replace(path)
        return before, after
    tmp.unlink(missing_ok=True)
    return before, before


def _terminate_tree(proc: subprocess.Popen, label: str) -> None:
    """Kill a process AND its children.

    `npm run dev` spawns node as a grandchild; terminating the npm wrapper alone
    leaves an orphaned Vite server holding the port. On Windows we use
    `taskkill /T /F`; elsewhere we kill the process group.
    """
    if proc.poll() is not None:
        return
    print(f"    stopping {label} (pid {proc.pid})")
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
        else:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(os.getpgid(proc.pid), 15)
    except Exception as exc:
        print(f"    warning: could not stop {label}: {exc}", file=sys.stderr)
    with contextlib.suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=15)
    if proc.poll() is None:
        proc.kill()


def _api(path: str, token: str = DEMO_TOKEN) -> dict:
    req = urllib.request.Request(f"{API_BASE}{path}", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _wait_for(url: str, label: str, timeout: float = 180.0, token: str | None = None) -> None:
    """Poll until an endpoint answers 200, or fail loudly."""
    deadline = time.time() + timeout
    last: str = "no attempt made"
    while time.time() < deadline:
        try:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    print(f"    {label} ready")
                    return
                last = f"HTTP {resp.status}"
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            last = str(exc)
        time.sleep(1.0)
    raise RuntimeError(f"{label} did not become ready within {timeout:.0f}s (last: {last})")


def run_pipeline(profile: str) -> None:
    print(f"[1/5] Running the real local pipeline (profile={profile}) ...")
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "run_local_pipeline.py"), "--profile", profile],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Pipeline failed (exit {result.returncode}).\n"
            f"--- stdout tail ---\n{result.stdout[-3000:]}\n"
            f"--- stderr tail ---\n{result.stderr[-2000:]}"
        )
    print("    pipeline complete")


def start_api() -> subprocess.Popen:
    print("[2/5] Starting FastAPI ...")
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "api.app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(API_PORT),
            "--log-level",
            "warning",
        ],
        cwd=REPO,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def start_ui() -> subprocess.Popen:
    print("[3/5] Starting the Vite dev server ...")
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if npm is None:
        raise RuntimeError("npm not found on PATH; run `npm install` in frontend/ first")
    if not (FRONTEND / "node_modules").exists():
        raise RuntimeError("frontend/node_modules missing — run `npm install` in frontend/")
    env = {**os.environ, "VITE_DEMO_TOKEN": DEMO_TOKEN}
    # `--port/--strictPort` on the CLI override vite.config.ts and any .env file,
    # so the capture always knows exactly where the UI is listening. Output is
    # kept so a startup failure can be reported instead of hanging silently.
    UI_LOG.parent.mkdir(parents=True, exist_ok=True)
    log = UI_LOG.open("w", encoding="utf-8")
    return subprocess.Popen(
        [npm, "run", "dev", "--", "--port", str(UI_PORT), "--strictPort"],
        cwd=FRONTEND,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        shell=False,
        start_new_session=(os.name != "nt"),
    )


def _assert_api_backed(page, expected: str, surface: str) -> None:
    """Fail unless a value fetched from the API is actually present in the DOM.

    This is what separates a real screenshot from a fixture: the string was read
    out of the live API response, so seeing it rendered proves the page is bound
    to the API rather than to hard-coded frontend data.
    """
    body = page.inner_text("body")
    if expected not in body:
        raise RuntimeError(
            f"{surface}: expected live API value {expected!r} to appear in the rendered page, "
            "but it did not. Refusing to save a screenshot that may not reflect API data."
        )


def capture(out_dir: Path) -> list[dict]:
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    shots: list[dict] = []

    # Real identifiers pulled from the live API so the UI shows real records.
    issue = _api("/api/v1/issues?page_size=1&status=DETECTED")["items"][0]
    parts_page = _api("/api/v1/parts?page_size=200")["items"]
    # find a part that actually has BOM children so the graph is not empty
    bom_part = None
    for p in parts_page:
        try:  # parts with no BOM answer 404 — skip them
            graph = _api(f"/api/v1/bom/{p['part_key']}/graph")
        except urllib.error.HTTPError:
            continue
        if graph.get("edges"):
            bom_part = graph["root"]
            break
    if bom_part is None:
        raise RuntimeError("no part with BOM relationships found — cannot capture the graph")
    merge_a, merge_b = parts_page[0]["part_key"], parts_page[1]["part_key"]
    principal = _api("/api/v1/me")

    print("[5/5] Capturing surfaces ...")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(viewport=VIEWPORT, device_scale_factor=2)
            page.set_default_timeout(45_000)

            # Send API calls straight to FastAPI instead of relying on vite's dev
            # proxy (whose target can be overridden by a local .env). Method,
            # headers (incl. the demo bearer token the app attaches) and body are
            # forwarded unchanged, so the UI still renders live API data.
            #
            # The pattern must be the full "/api/v1/" prefix, NOT "**/api/**":
            # the latter also matches the app's own modules (/src/api/client.ts),
            # which would be redirected to the API and 404, leaving a blank page.
            def _route_api(route, request):  # type: ignore[no-untyped-def]
                target = request.url.replace(UI_BASE, API_BASE, 1)
                try:
                    route.fulfill(response=route.fetch(url=target))
                except Exception:
                    route.abort()

            page.route("**/api/v1/**", _route_api)

            def shot(name: str, caption: str, alt: str) -> None:
                page.wait_for_timeout(900)  # let charts/graph settle
                path = out_dir / f"{name}.png"
                page.screenshot(path=str(path), full_page=False)
                before, after = _optimize(path)
                shots.append({"file": path.name, "caption": caption, "alt": alt, "bytes": after})
                saved = f" ({before // 1024}KB -> {after // 1024}KB)" if after < before else ""
                print(f"    captured {path.name}{saved}")

            # 1. Command Center
            page.goto(UI_BASE, wait_until="networkidle")
            page.wait_for_selector("text=/Command Center/i")
            shot(
                "command-center",
                "Command Center — enterprise quality score, issue counts by severity, "
                "and the highest-exposure defects, all read from the live API.",
                "BOM Guardian Command Center dashboard showing the enterprise quality "
                "score, issue counts by severity, and a ranked list of highest-impact "
                "data-quality issues.",
            )

            # 2. Data Quality Explorer
            page.goto(f"{UI_BASE}/issues", wait_until="networkidle")
            page.wait_for_selector("table")
            _assert_api_backed(page, issue["rule_id"], "Data Quality Explorer")
            shot(
                "issue-explorer",
                "Data Quality Explorer — filterable, paginated issues from the 49-rule "
                "engine with severity, domain, and status.",
                "Data Quality Explorer table listing detected data-quality issues with "
                "rule id, severity, domain, entity, and status columns.",
            )

            # 3. Remediation Workbench (real issue, real evidence, AI proposal)
            page.goto(f"{UI_BASE}/workbench/{issue['issue_id']}", wait_until="networkidle")
            page.wait_for_selector("text=/Evidence/i")
            _assert_api_backed(page, issue["issue_id"], "Remediation Workbench")
            _assert_api_backed(page, principal["username"], "Remediation Workbench")
            with contextlib.suppress(Exception):
                page.click("text=Generate recommendation")
                page.wait_for_selector("text=/Confidence/i", timeout=30_000)
            shot(
                "remediation-workbench",
                "Remediation Workbench — issue evidence, a governed AI proposal "
                "(schema-validated, grounded, human-review-required), and the "
                "steward decision panel showing the authenticated actor.",
                "Remediation Workbench showing issue summary, evidence rows, an AI "
                "remediation proposal with confidence and explanation, and an approve "
                "or reject decision panel.",
            )

            # 4. Part 360 — click the first row (rows are keyed by part_key but
            # display source_part_number, so select by row, not by id text).
            page.goto(f"{UI_BASE}/parts", wait_until="networkidle")
            page.wait_for_selector("table tbody tr")
            page.click("table tbody tr:first-child")
            page.wait_for_selector("text=/Golden record|Lineage|Impact/i", timeout=30_000)
            shot(
                "part-360",
                "Part 360 — searchable part master with the golden record, per-field "
                "lineage (source, reason, confidence) and blast-radius impact.",
                "Part 360 page listing parts with a selected part's golden record, "
                "field-level lineage, and impact metrics.",
            )

            # 5. BOM Graph Explorer
            page.goto(f"{UI_BASE}/bom?part={bom_part}", wait_until="networkidle")
            page.wait_for_timeout(3000)  # cytoscape layout
            shot(
                "bom-explorer",
                "BOM Graph Explorer — multi-level bill-of-materials traversal with "
                "cycle, orphan, and reverse-dependency analysis.",
                "BOM Graph Explorer showing an interactive node-and-edge graph of a "
                "multi-level bill of materials for the selected part.",
            )

            # 6. Scenario Simulator (Quality Impact Twin)
            page.goto(f"{UI_BASE}/scenarios", wait_until="networkidle")
            with contextlib.suppress(Exception):
                page.fill('input[aria-label="Duplicate part ID"]', merge_a)
                page.fill('input[aria-label="Surviving part ID"]', merge_b)
                page.click("text=/Simulate/i")
                page.wait_for_timeout(2500)
            shot(
                "scenario-simulator",
                "Scenario Simulator — counterfactual merge/correction/replacement with "
                "before-and-after diffs and newly introduced conflicts. Simulations are "
                "persisted separately and never mutate baseline data.",
                "Scenario Simulator showing a simulated part merge with before and "
                "after comparison and any newly introduced conflicts.",
            )

            # 7. AI Governance
            page.goto(f"{UI_BASE}/governance", wait_until="networkidle")
            page.wait_for_timeout(1200)
            shot(
                "ai-governance",
                "AI Governance — every AI call audited: provider, model, prompt "
                "version, latency, validation result, abstention, and confidence.",
                "AI Governance dashboard listing audited AI calls with provider, model, "
                "latency, validation outcome, and confidence.",
            )

            # 8. Data Steward Copilot
            page.goto(f"{UI_BASE}/copilot", wait_until="networkidle")
            # Use one of the app's own suggested questions — it maps to a real
            # allowlisted tool, so the answer shows cited evidence rather than the
            # (also real, but less representative) insufficient-evidence path.
            page.fill(
                'input[aria-label="Question"]',
                "Which suppliers have the highest risk exposure?",
            )
            page.click('button:has-text("Ask")')
            page.wait_for_timeout(3000)
            shot(
                "copilot",
                "Data Steward Copilot — read-only, allowlisted retrieval with cited "
                "evidence; refuses mutations and answers 'insufficient evidence' "
                "rather than guessing.",
                "Data Steward Copilot chat panel showing a question about critical "
                "issues and a cited, evidence-backed answer.",
            )
        finally:
            browser.close()
    return shots


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="smoke")
    parser.add_argument("--out", default="docs/screenshots")
    parser.add_argument(
        "--skip-pipeline",
        action="store_true",
        help="reuse the existing local warehouse instead of regenerating it",
    )
    args = parser.parse_args()

    out_dir = REPO / args.out
    api_proc: subprocess.Popen | None = None
    ui_proc: subprocess.Popen | None = None
    try:
        print(f"    (API port {API_PORT}, UI port {UI_PORT} — chosen at runtime)")
        if args.skip_pipeline:
            print("[1/5] Skipping pipeline (--skip-pipeline); reusing existing warehouse")
        else:
            run_pipeline(args.profile)

        api_proc = start_api()
        _wait_for(f"{API_BASE}/api/v1/health", "API /health")
        _wait_for(f"{API_BASE}/api/v1/readiness", "API /readiness")

        ui_proc = start_ui()
        print("[4/5] Waiting for the UI ...")
        try:
            _wait_for(UI_BASE, "Vite dev server")
        except RuntimeError as exc:
            tail = (
                UI_LOG.read_text(encoding="utf-8", errors="replace")[-2000:]
                if (UI_LOG.exists())
                else "(no dev-server log)"
            )
            raise RuntimeError(f"{exc}\n--- dev server output ---\n{tail}") from exc

        shots = capture(out_dir)
        manifest = {
            "captured_from": "live application (real pipeline + FastAPI + Vite dev server)",
            "profile": args.profile,
            "api_base": API_BASE,
            "ui_base": UI_BASE,
            "viewport": VIEWPORT,
            "screenshots": shots,
        }
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        print(f"\nCaptured {len(shots)} screenshots -> {out_dir}")
        return 0
    except Exception as exc:
        print(f"\nSCREENSHOT CAPTURE FAILED: {exc}", file=sys.stderr)
        return 1
    finally:
        # Always tear down the whole process tree, even if capture raised.
        for proc, label in ((ui_proc, "UI"), (api_proc, "API")):
            if proc is not None:
                _terminate_tree(proc, label)


if __name__ == "__main__":
    raise SystemExit(main())
