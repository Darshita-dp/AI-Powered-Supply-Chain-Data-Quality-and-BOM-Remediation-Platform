# Security Policy

## Reporting

This is a portfolio project using only synthetic data. If you find a vulnerability,
open a GitHub issue or contact the repository owner.

## Design commitments

- No real supplier, part, pricing, or personal data anywhere in the repository.
- No credentials in code or git history; configuration via environment variables
  (`.env` is git-ignored, `.env.example` documents the surface).
- AI providers are read-only with respect to golden/master data; all remediation
  changes require human approval and are audited.
- Supplier document content is treated as untrusted input (prompt-injection controls).
- CORS restricted by default; structured errors without stack traces.

The full threat model lives in `docs/security-model.md` (added in milestone M19).
