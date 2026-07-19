# Application screenshots

Every image here is a **real capture of the running application** — no mockups, no
hand-edited values, no fixture data. They are produced by
[`scripts/capture_screenshots.py`](../../scripts/capture_screenshots.py).

## How they are produced

```bash
pip install -e ".[dev,api,ml,docs-ai,dbt]"
pip install playwright && python -m playwright install chromium
cd frontend && npm install && cd ..

make screenshots           # or: python scripts/capture_screenshots.py
                           # or: cd frontend && npm run screenshots
```

The script:

1. runs the real local pipeline (generate → inject → ingest → dbt → rules → marts),
2. starts the real FastAPI service and the real Vite dev server on runtime-selected
   free ports,
3. waits for `/health` and `/readiness`,
4. authenticates with the documented demo steward bearer token,
5. drives the live UI with Playwright — typing part and issue ids it read from the
   API, clicking through to generate an AI proposal, run a merge simulation, and ask
   the Copilot a question,
6. writes optimized PNGs plus `manifest.json` (file, caption, alt text, size), and
7. tears down every process in a `finally` block, killing the whole process tree.

`--skip-pipeline` reuses an existing warehouse; the script exits non-zero and saves
nothing rather than emitting a placeholder if any step fails.

## Why these are real, not fixtures

The frontend has no mock-data path — every page reads the API. On top of that, the
script asserts that specific values it fetched from the API (issue id, rule id, the
authenticated principal) are actually present in the rendered DOM before saving a
screenshot (`_assert_api_backed`). A page that rendered fixtures or an error state
fails the run instead of producing a misleading image.

`tests/unit/test_screenshot_capture.py` guards the harness itself (route scoping,
IPv6/localhost binding, process-tree teardown) and verifies every committed PNG is a
real image of plausible size with alt text and a caption.

## The surfaces

| File | Surface |
|---|---|
| `command-center.png` | Enterprise quality posture, issues by domain, top priorities |
| `issue-explorer.png` | Data Quality Explorer — filterable, paginated 49-rule output |
| `remediation-workbench.png` | Issue evidence, governed AI proposal, steward decision panel |
| `part-360.png` | Golden record with field-level lineage, blast radius, open issues |
| `bom-explorer.png` | Multi-level BOM graph with reverse dependencies |
| `scenario-simulator.png` | Counterfactual merge: before/after, rules resolved, new conflicts |
| `ai-governance.png` | Audited AI calls: provider, model, latency, validation, confidence |
| `copilot.png` | Read-only Copilot answer with cited evidence references |

All data shown is synthetic (seeded generator output). Numbers vary with the profile
and seed used for the capture run — see `manifest.json` for the run's parameters.
