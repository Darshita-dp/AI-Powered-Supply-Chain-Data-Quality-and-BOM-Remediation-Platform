"""Copilot tests: classification, grounding, refusal, read-only guarantee."""

import inspect

import pytest

from bom_guardian.copilot import Copilot
from bom_guardian.copilot import tools as copilot_tools
from bom_guardian.quality import RuleEngine
from bom_guardian.testing import build_test_warehouse


@pytest.fixture(scope="module")
def copilot(tmp_path_factory):  # type: ignore[no-untyped-def]
    wh = build_test_warehouse(tmp_path_factory.mktemp("copilot"), n_parts=300, seed=11)
    RuleEngine(wh).run_all()
    yield Copilot(wh)
    wh.close()


def _an_entity_with_issues(copilot: Copilot) -> str:
    df = copilot.wh.query(
        "SELECT entity_key FROM quality.dq_issues WHERE entity_type = 'part' LIMIT 1"
    )
    return str(df.iloc[0]["entity_key"])


def test_refuses_mutation_requests(copilot) -> None:  # type: ignore[no-untyped-def]
    answer = copilot.query("Please approve issue ISS-123 for me")
    assert answer.refused
    assert "cannot approve" in answer.answer


def test_entity_issue_question_is_cited(copilot) -> None:  # type: ignore[no-untyped-def]
    entity = _an_entity_with_issues(copilot)
    answer = copilot.query(f"What issues does {entity} have?")
    assert answer.classification == "entity_issues"
    assert answer.rows
    assert answer.citations
    assert all(c.startswith("quality.dq_issues:") for c in answer.citations)


def test_failed_rules_question(copilot) -> None:  # type: ignore[no-untyped-def]
    entity = _an_entity_with_issues(copilot)
    answer = copilot.query(f"Which rules failed for {entity}?")
    assert answer.classification == "failed_rules"
    assert answer.rows


def test_obsolete_demand_question(copilot) -> None:  # type: ignore[no-untyped-def]
    answer = copilot.query("Which obsolete components affect the most future demand?")
    assert answer.classification == "obsolete_demand"
    assert not answer.refused


def test_supplier_risk_question(copilot) -> None:  # type: ignore[no-untyped-def]
    answer = copilot.query("Which suppliers have the highest unresolved risk exposure?")
    assert answer.classification == "supplier_risk"
    assert answer.rows


def test_unknown_entity_reports_insufficient_evidence(copilot) -> None:  # type: ignore[no-untyped-def]
    answer = copilot.query("What issues does PRT999999 have?")
    assert answer.insufficient_evidence
    assert "insufficient" in answer.answer.lower()


def test_unsupported_question_degrades_gracefully(copilot) -> None:  # type: ignore[no-untyped-def]
    answer = copilot.query("What's the weather like in Chicago?")
    assert answer.classification == "unsupported"
    assert answer.insufficient_evidence


def test_all_tools_are_read_only() -> None:
    """No tool source may contain mutating SQL keywords."""
    source = inspect.getsource(copilot_tools)
    for keyword in ("INSERT ", "UPDATE ", "DELETE ", "DROP ", "CREATE TABLE", "ALTER "):
        assert keyword not in source.upper().replace("\n", " "), keyword
