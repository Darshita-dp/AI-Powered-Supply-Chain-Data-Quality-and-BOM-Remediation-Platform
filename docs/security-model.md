# Security Model and Threat Assessment — BOM Guardian AI

## Controls implemented

| Control | Where |
|---|---|
| No credentials in code; env-based config with `.env.example` | `src/bom_guardian/config/settings.py` |
| Secret scanning (gitleaks) in pre-commit + CI | `.pre-commit-config.yaml`, `.github/workflows/ci.yml` |
| Restricted CORS (explicit origin list, GET/POST only) | `api/app/main.py` |
| Request validation (Pydantic bodies, bounded pagination, sort-column allowlists) | `api/app/routers/*` |
| Structured errors without stack traces + correlation IDs | `api/app/main.py` |
| AI providers cannot write; proposals schema-validated + grounded; mandatory human review | `src/bom_guardian/ai/` |
| AI call budget/timeout settings | `settings.py` (`ai_call_budget`, `ai_timeout_seconds`) |
| Copilot: allowlisted parameterized SELECT tools only; mutation refusal | `src/bom_guardian/copilot/` |
| Document text treated as untrusted; instruction patterns flagged, never followed; extracted fields type/set-validated | `src/bom_guardian/document_intelligence/` |
| Decision lifecycle guards + full remediation audit | `api/app/services/` |
| Snowflake role separation (admin/engineer/app/analyst; ground truth restricted) | `warehouse/snowflake/security/` |
| Structured JSON logging without secrets or document bodies | `src/bom_guardian/observability/` |

## Threat model (top risks)

| # | Risk | Mitigation | Residual |
|---|---|---|---|
| 1 | Incorrect entity consolidation (wrong merge) | Precision-favoring thresholds, abstain band, no auto-merge, human approval, scenario preview, reversible field lineage | Reviewer error remains possible; feedback loop surfaces override rates |
| 2 | Hallucinated AI explanations | Grounding validation rejects evidence refs not in the bundle; schema validation; deterministic mock in tests | Live-provider phrasing may still mislead; explanation limited to evidence text |
| 3 | Prompt injection via supplier documents | Deterministic extraction first; instruction-pattern flagging; delimited untrusted content; schema-constrained AI output; field validation | Novel injection phrasings may evade the pattern list; flagged docs go to review |
| 4 | Unauthorized remediation approval | Only the human decision endpoint mutates status; AI has no approve action in its schema; transitions guarded; every decision audited | No authn in the portfolio build — add SSO before any real deployment |
| 5 | Exposure of supplier information | All data synthetic; no PII generated; logs exclude document bodies | N/A for synthetic data; real deployments need data classification |
| 6 | Data poisoning through feedback | No automatic retraining; feedback only reported | — |
| 7 | Model drift | Versioned models + prompt versions audited per call; evaluation reports reproducible | No scheduled re-evaluation job yet |
| 8 | Excessive AI cost | Call budget setting; deterministic mock default; latency/cost fields audited | Budget enforcement is per-run configuration, not hard metering |
| 9 | Stale data | TEMP rules detect stale records; load audit timestamps everything | — |
| 10 | Incorrect graph propagation (bad blast radius) | Graph module unit-tested on all structural shapes incl. cycle corruption; simulations never mutate baseline | Exposure figures are estimates; documented in `limitations.md` |

## Known gaps (honest)

- **No authentication/authorization on the API or UI** — this is a single-user local
  portfolio build. Reviewer identity is self-declared. Production would require SSO,
  role checks on decision endpoints, and rate limiting.
- SQL identifiers are quoted via escaping helpers rather than fully parameterized
  bindings in some warehouse paths (DuckDB local trust boundary); Snowflake deployment
  should switch to bound parameters throughout.
- Dependency versions are lower-bounded, not fully locked; `frontend/package-lock.json`
  is locked, Python uses `pyproject.toml` ranges.
