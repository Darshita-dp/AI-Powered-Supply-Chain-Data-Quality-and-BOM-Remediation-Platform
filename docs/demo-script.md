# Demo Script — BOM Guardian AI (~10 minutes)

## Setup (once)

```bash
python -m venv .venv && . .venv/Scripts/activate
pip install -e ".[dev,api,ml,dbt]"
python scripts/run_local_pipeline.py          # generate → inject → ingest → dbt → rules → marts
uvicorn api.app.main:app --port 8000          # terminal 1
cd frontend && npm install && npm run dev     # terminal 2 → http://localhost:5173
```

## Storyline

1. **Command Center (1 min).** "This is a synthetic manufacturer with 5 source systems.
   The pipeline just detected ~1,300 data-quality issues across 49 rules; enterprise
   score, inventory exposure, and the critical queue are live from the warehouse."
2. **Data Quality Explorer (1 min).** Filter severity = critical, domain = graph
   integrity → circular-BOM findings. "Every issue carries reproducible rule logic and
   evidence."
3. **Issue detail / Remediation Workbench (3 min).** Open a GRPH cycle issue:
   evidence row shows the exact offending edge. Click *Generate recommendation* —
   the governed AI proposal appears with confidence, provider, and an explanation that
   cites evidence IDs. Point out: `human_review_required` is always true; the AI cannot
   approve. Approve as yourself with a reason → status flips, decision history shows
   the audit record.
4. **Part 360 (1.5 min).** Search a part → golden record table: description sourced
   from PLM, cost from ERP, lead time from the supplier portal — each with confidence
   and alternatives (field-level survivorship).
5. **BOM Graph Explorer (1.5 min).** Explore an assembly; cycles glow pink, obsolete
   components red. Reverse dependencies show the blast radius upward.
6. **Scenario Simulator (1.5 min).** Merge a duplicate into its original: before/after,
   resolved rules, and — merge into an OBSOLETE part instead — a new warning appears.
   "Simulations never touch baseline data; the E2E test asserts that."
7. **Copilot + AI Governance (30s).** Ask "Which suppliers have the highest risk
   exposure?" → cited answer. Ask it to approve something → refusal. Governance page
   shows every AI call audited.

## Proof points to mention

- 136 automated tests incl. a 12-step end-to-end test.
- Detection recall 100% on 156 injected, ground-truth-labeled defects (17 types).
- ER: precision-first (P=1.00 measured) with confidence bands and abstention.
- Reproducible: one seed, one command, same numbers.
