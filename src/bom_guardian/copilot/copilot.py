"""Copilot orchestration: classify → allowlisted retrieval → cited answer.

Classification is deterministic (keyword rules), which keeps the copilot fully
testable without an AI provider; an AI provider could later rewrite answers
but never gains query access beyond the tool allowlist. Governance:
- read-only by construction (only tools.py functions run, all SELECT);
- refuses approval/mutation requests outright;
- states insufficiency instead of guessing;
- every answer carries citations to the exact records used.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bom_guardian.copilot import tools
from bom_guardian.observability import get_logger
from bom_guardian.warehouse import LocalWarehouse

_PART_ID = re.compile(r"\b(PRT\w{4,})\b", re.IGNORECASE)
_PLANT_ID = re.compile(r"\b(PL\d{2})\b", re.IGNORECASE)
_MUTATION = re.compile(
    r"\b(approve|reject|apply|merge now|delete|update|fix it|change the)\b", re.IGNORECASE
)


@dataclass
class CopilotAnswer:
    question: str
    classification: str
    answer: str
    rows: list[dict] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    insufficient_evidence: bool = False
    refused: bool = False


class Copilot:
    def __init__(self, warehouse: LocalWarehouse) -> None:
        self.wh = warehouse
        self._log = get_logger("copilot")

    def query(self, question: str) -> CopilotAnswer:
        q = question.strip()
        part = _PART_ID.search(q)
        plant = _PLANT_ID.search(q)

        if _MUTATION.search(q):
            return CopilotAnswer(
                question=q,
                classification="mutation_request",
                answer=(
                    "I can explain issues and evidence, but I cannot approve, apply, or "
                    "change master data. Please use the Remediation Workbench, where "
                    "decisions are made by a human reviewer and audited."
                ),
                refused=True,
            )

        lowered = q.lower()
        if "duplicate" in lowered and part:
            return self._answer(
                q,
                "duplicate_explanation",
                tools.duplicate_explanation(self.wh, part.group(1).upper()),
                lambda rows: (
                    f"{part.group(1).upper()} was flagged by uniqueness rules; the evidence "
                    f"values show which identifiers collide: "
                    + "; ".join(str(r.get("failed_value")) for r in rows[:3])
                ),
            )
        if ("rule" in lowered and "fail" in lowered) and part:
            return self._answer(
                q,
                "failed_rules",
                tools.failed_rules_for_entity(self.wh, part.group(1).upper()),
                lambda rows: (
                    f"{len(rows)} rule(s) failed for {part.group(1).upper()}: "
                    + ", ".join(f"{r['rule_id']} ({r['name']})" for r in rows[:5])
                ),
            )
        if ("depend" in lowered or "assembl" in lowered) and part:
            return self._answer(
                q,
                "reverse_dependencies",
                tools.assemblies_depending_on(self.wh, part.group(1).upper()),
                lambda rows: (
                    f"{len(rows)} assembly/assemblies depend on {part.group(1).upper()}: "
                    + ", ".join(r["assembly"] for r in rows[:10])
                ),
            )
        if "obsolete" in lowered and "demand" in lowered:
            return self._answer(
                q,
                "obsolete_demand",
                tools.obsolete_components_by_demand(self.wh),
                lambda rows: (
                    "Obsolete parts with the highest future demand: "
                    + ", ".join(f"{r['part_key']} ({r['demand_qty']:.0f})" for r in rows[:5])
                ),
            )
        if "supplier" in lowered and ("risk" in lowered or "exposure" in lowered):
            return self._answer(
                q,
                "supplier_risk",
                tools.supplier_risk_exposure(self.wh),
                lambda rows: (
                    "Suppliers with the most open data-quality exposure: "
                    + ", ".join(f"{r['supplier_id']} ({r['open_issues']} issues)" for r in rows[:5])
                ),
            )
        if plant and ("issue" in lowered or "risk" in lowered):
            return self._answer(
                q,
                "plant_issues",
                tools.issues_for_plant(self.wh, plant.group(1)),
                lambda rows: (
                    f"{len(rows)} high/critical issue(s) touch parts at {plant.group(1).upper()}: "
                    + ", ".join(f"{r['rule_id']}@{r['entity_key']}" for r in rows[:5])
                ),
            )
        if "abstain" in lowered or "abstention" in lowered:
            return self._answer(
                q,
                "ai_abstentions",
                tools.ai_abstentions(self.wh),
                lambda rows: (
                    f"{len(rows)} recent abstention(s). The model abstains when the evidence "
                    "bundle is too sparse to ground a recommendation."
                ),
            )
        if part:
            return self._answer(
                q,
                "entity_issues",
                tools.issues_for_entity(self.wh, part.group(1).upper()),
                lambda rows: (
                    f"{part.group(1).upper()} has {len(rows)} recorded issue(s): "
                    + ", ".join(f"{r['rule_id']} [{r['severity']}]" for r in rows[:5])
                ),
            )

        return CopilotAnswer(
            question=q,
            classification="unsupported",
            answer=(
                "I couldn't map that question to my governed data tools. I can answer "
                "questions about a part's issues, failed rules, duplicates, dependent "
                "assemblies, obsolete parts with demand, supplier risk exposure, plant "
                "issues, and AI abstentions."
            ),
            insufficient_evidence=True,
        )

    def _answer(self, q: str, classification: str, result: dict, phrase) -> CopilotAnswer:  # type: ignore[no-untyped-def]
        rows = result["rows"]
        if not rows:
            return CopilotAnswer(
                question=q,
                classification=classification,
                answer="No supporting records were found — insufficient evidence to answer.",
                insufficient_evidence=True,
                citations=result["citations"],
            )
        answer = CopilotAnswer(
            question=q,
            classification=classification,
            answer=phrase(rows),
            rows=rows,
            citations=result["citations"],
        )
        self._log.info("copilot_answer", classification=classification, rows=len(rows))
        return answer
