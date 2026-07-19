# API Guide — BOM Guardian AI

Base URL: `http://127.0.0.1:8000/api/v1` · Interactive docs: `/api/v1/docs` (OpenAPI).
All responses JSON; errors are structured (`error`, `detail`, `correlation_id`) with no
stack traces; every response carries `X-Correlation-ID`.

## Authorization (demonstration)

Every `/api/v1` business endpoint (parts, issues, bom, scenarios, analytics, copilot)
requires an `Authorization: Bearer <token>` header; `/health`, `/readiness`, and
`/metrics` are open. This is **demonstration auth**, not enterprise SSO — three static
demo tokens map to the three roles (override via the `BOMG_DEMO_USERS` env var):

| Token | Role | Can do |
|---|---|---|
| `demo-analyst-token` | analyst | read parts/issues/analytics/bom/copilot, generate draft proposals, run scenarios |
| `demo-steward-token` | steward | analyst + **approve / reject / request-evidence** |
| `demo-admin-token` | admin | steward + (reserved) configuration |

Missing or unknown token → 401; authenticated but insufficient role → 403. The reviewer
recorded on a decision is the **authenticated principal**, never a value in the request
body. Example: `curl -H "Authorization: Bearer demo-steward-token" .../issues`.

## Endpoints (26)

### Platform
| Method | Path | Notes |
|---|---|---|
| GET | /health | liveness + version |
| GET | /readiness | verifies all warehouse schemas |
| GET | /metrics | part count, issues by status |
| GET | /me | the authenticated principal (`username`, `role`) — the UI shows this as the actor a decision will be recorded against |

### Parts
| GET | /parts | pagination (`page`, `page_size`≤200), `search`, `category`, `lifecycle_status`, `plant`, `sort_by` (allowlisted), `sort_dir` |
|---|---|---|
| GET | /parts/{id} | full dim_part record |
| GET | /parts/{id}/sources | aliases / source references |
| GET | /parts/{id}/lineage | golden record with per-field source, reason, confidence, alternatives |
| GET | /parts/{id}/impact | blast radius (assemblies, demand, inventory, POs, suppliers, plants, priority) |

### Issues & remediation
| GET | /issues | filters: `severity`, `domain`, `rule_id`, `status`, `entity_key`; sorted, paginated |
|---|---|---|
| GET | /issues/{id} · /evidence · /history | detail, failed values, decision audit |
| POST | /issues/{id}/recommendations | governed AI proposal (mock provider by default); never mutates |
| POST | /issues/{id}/approve · /reject · /request-evidence | **requires steward/admin**; body `{reason}` (actor taken from the auth principal); lifecycle-guarded (409 on invalid transition); audited |

### BOM graph
| GET | /bom/{id}/graph?depth=1..10 | nodes (with lifecycle + cycle flags), edges, cycles |
|---|---|---|
| GET | /bom/{id}/dependencies · /reverse-dependencies | downstream / upstream closure |

### Scenarios
| POST | /scenarios/merge · /field-correction · /component-replacement | before/after, resolved rules, new warnings; persisted, baseline untouched |
|---|---|---|
| GET | /scenarios/{id} | retrieve a persisted simulation |

### Analytics & copilot
| GET | /analytics/quality · /business-impact · /remediation · /ai-governance | marts-backed aggregates |
|---|---|---|
| POST | /copilot/query | body `{question}`; cited, read-only, refuses mutations |

## Running

```bash
python scripts/run_local_pipeline.py     # build the warehouse first
uvicorn api.app.main:app --port 8000
```

The API serves `warehouse/local/bom_guardian.duckdb` (path via `BOMG_DUCKDB_PATH`).
No authentication is implemented — see [security-model.md](security-model.md).
