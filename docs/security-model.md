# Security Model and Threat Assessment — BOM Guardian AI

## Controls implemented

| Control | Where |
|---|---|
| No credentials in code; env-based config with `.env.example` | `src/bom_guardian/config/settings.py` |
| Secret scanning (gitleaks, full default rule set) in pre-commit + CI over full history | `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `.gitleaks.toml` |
| Restricted CORS (explicit origin list, GET/POST only) | `api/app/main.py` |
| Request validation (Pydantic bodies, bounded pagination, sort-column allowlists) | `api/app/routers/*` |
| Structured errors without stack traces + correlation IDs | `api/app/main.py` |
| Role-based authorization (analyst/steward/admin); decisions require steward+; authenticated actor recorded, not trusted from the body — **demonstration auth**, not enterprise IdP | `api/app/auth.py` |
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
| 4 | Unauthorized remediation approval | Approve/reject/request-evidence require a steward or admin role (`require_role`); the recorded actor is the authenticated principal, not a body-supplied name; AI has no approve action in its schema; transitions guarded; every decision audited | Authentication is **demonstration-grade** (static demo bearer tokens); a real deployment must swap in SSO/OIDC identities — the authorization logic stays |
| 5 | Exposure of supplier information | All data synthetic; no PII generated; logs exclude document bodies | N/A for synthetic data; real deployments need data classification |
| 6 | Data poisoning through feedback | No automatic retraining; feedback only reported | — |
| 7 | Model drift | Versioned models + prompt versions audited per call; evaluation reports reproducible | No scheduled re-evaluation job yet |
| 8 | Excessive AI cost | Call budget setting; deterministic mock default; latency/cost fields audited | Budget enforcement is per-run configuration, not hard metering |
| 9 | Stale data | TEMP rules detect stale records; load audit timestamps everything | — |
| 10 | Incorrect graph propagation (bad blast radius) | Graph module unit-tested on all structural shapes incl. cycle corruption; simulations never mutate baseline | Exposure figures are estimates; documented in `limitations.md` |

## Known gaps (honest)

- **Authentication is demonstration-grade, not production IAM.** The API enforces a real
  role ladder (analyst/steward/admin) and gates decision endpoints on steward+, recording
  the authenticated principal rather than a self-declared name. But identities come from
  static demo bearer tokens (`api/app/auth.py`, overridable via `BOMG_DEMO_USERS`), not an
  SSO/OIDC provider, and there is no session management, token expiry, or rate limiting.
  A production deployment must replace the token store with a corporate IdP; the
  authorization checks themselves carry over unchanged.
- SQL identifiers are quoted via escaping helpers rather than fully parameterized
  bindings in some warehouse paths (DuckDB local trust boundary); Snowflake deployment
  should switch to bound parameters throughout.
- Dependency versions are lower-bounded, not fully locked; `frontend/package-lock.json`
  is locked, Python uses `pyproject.toml` ranges.
- **Secret scanning carries one documented allowlist.** `.gitleaks.toml` extends the full
  default rule set and allowlists exactly three literal strings —
  `demo-analyst-token`, `demo-steward-token`, `demo-admin-token` — because the
  `curl-auth-header` rule flags them wherever the docs show an authenticated `curl`
  example. They are intentionally public, non-functional demonstration credentials
  defined in `api/app/auth.py`. The allowlist is scoped to those exact strings: a real
  bearer token in the *same* curl example is still detected (verified by scanning a
  planted credential). No rule is disabled.
