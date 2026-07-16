"""Rule execution engine: runs registered rules, persists executions, issues,
and evidence into the quality schema."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pandas as pd

from bom_guardian.observability import get_logger
from bom_guardian.quality.models import Rule
from bom_guardian.quality.registry import enabled_rules
from bom_guardian.warehouse import LocalWarehouse

_QUALITY_DDL = [
    """
    CREATE TABLE IF NOT EXISTS quality.dq_rules (
        rule_id VARCHAR, name VARCHAR, description VARCHAR, domain VARCHAR,
        severity VARCHAR, rule_type VARCHAR, owner_role VARCHAR, threshold DOUBLE,
        enabled BOOLEAN, version INTEGER, effective_date DATE,
        remediation_guidance VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS quality.dq_rule_executions (
        execution_id VARCHAR, rule_id VARCHAR, rule_version INTEGER,
        run_id VARCHAR, executed_at TIMESTAMP, violations INTEGER,
        duration_ms DOUBLE, status VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS quality.dq_issues (
        issue_id VARCHAR, rule_id VARCHAR, execution_id VARCHAR, run_id VARCHAR,
        entity_type VARCHAR, entity_key VARCHAR, field VARCHAR,
        severity VARCHAR, domain VARCHAR, status VARCHAR,
        detected_at TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS quality.dq_issue_evidence (
        evidence_id VARCHAR, issue_id VARCHAR, field VARCHAR,
        failed_value VARCHAR, rule_sql_version INTEGER, detected_at TIMESTAMP
    )
    """,
]


class RuleEngine:
    """Executes the rule registry against a warehouse and persists results."""

    def __init__(self, warehouse: LocalWarehouse, rules: list[Rule] | None = None) -> None:
        self.wh = warehouse
        self.rules = rules if rules is not None else enabled_rules()
        self._log = get_logger("rule_engine")
        for ddl in _QUALITY_DDL:
            self.wh.execute(ddl)

    def sync_rule_definitions(self) -> None:
        """Refresh quality.dq_rules from the registry (registry is source of truth)."""
        df = pd.DataFrame(
            [
                {
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "description": r.description,
                    "domain": r.domain.value,
                    "severity": r.severity.value,
                    "rule_type": r.rule_type,
                    "owner_role": r.owner_role,
                    "threshold": r.threshold,
                    "enabled": r.enabled,
                    "version": r.version,
                    "effective_date": r.effective_date,
                    "remediation_guidance": r.remediation_guidance,
                }
                for r in self.rules
            ]
        )
        self.wh.load_dataframe("quality", "dq_rules", df, replace=True)

    def run_all(self) -> dict:
        """Execute every enabled rule. Returns run summary."""
        run_id = f"DQRUN-{uuid.uuid4().hex[:12]}"
        log = self._log.bind(run_id=run_id)
        self.sync_rule_definitions()
        total_issues = 0
        failures: list[str] = []
        for rule in self.rules:
            n = self._run_rule(rule, run_id, failures)
            total_issues += n
        summary = {
            "run_id": run_id,
            "rules_executed": len(self.rules),
            "rules_failed": len(failures),
            "failed_rules": failures,
            "issues_created": total_issues,
        }
        log.info("dq_run_complete", **{k: v for k, v in summary.items() if k != "failed_rules"})
        return summary

    def _run_rule(self, rule: Rule, run_id: str, failures: list[str]) -> int:
        execution_id = f"EXEC-{uuid.uuid4().hex[:12]}"
        started = datetime.now(UTC)
        try:
            violations = self.wh.query(rule.sql)
        except Exception as exc:  # rule SQL failure must not kill the run
            self._log.error("rule_failed", rule_id=rule.rule_id, error=str(exc))
            failures.append(rule.rule_id)
            self._record_execution(execution_id, rule, run_id, started, 0, "FAILED")
            return 0

        violations.columns = ["entity_type", "entity_key", "field", "failed_value"][
            : len(violations.columns)
        ]
        now = datetime.now(UTC)
        n = len(violations)
        if n:
            issues = pd.DataFrame(
                {
                    "issue_id": [f"ISS-{uuid.uuid4().hex[:12]}" for _ in range(n)],
                    "rule_id": rule.rule_id,
                    "execution_id": execution_id,
                    "run_id": run_id,
                    "entity_type": violations["entity_type"].astype(str),
                    "entity_key": violations["entity_key"].astype(str),
                    "field": violations.get("field", pd.Series([None] * n)),
                    "severity": rule.severity.value,
                    "domain": rule.domain.value,
                    "status": "DETECTED",
                    "detected_at": now,
                }
            )
            self.wh.load_dataframe("quality", "dq_issues", issues, replace=False)
            evidence = pd.DataFrame(
                {
                    "evidence_id": [f"EVD-{uuid.uuid4().hex[:12]}" for _ in range(n)],
                    "issue_id": issues["issue_id"],
                    "field": issues["field"],
                    "failed_value": violations.get("failed_value", pd.Series([None] * n)).astype(
                        "string"
                    ),
                    "rule_sql_version": rule.version,
                    "detected_at": now,
                }
            )
            self.wh.load_dataframe("quality", "dq_issue_evidence", evidence, replace=False)
        self._record_execution(execution_id, rule, run_id, started, n, "COMPLETED")
        return n

    def _record_execution(
        self, execution_id: str, rule: Rule, run_id: str, started: datetime, n: int, status: str
    ) -> None:
        duration_ms = (datetime.now(UTC) - started).total_seconds() * 1000
        self.wh.execute(
            "INSERT INTO quality.dq_rule_executions VALUES "
            f"('{execution_id}', '{rule.rule_id}', {rule.version}, '{run_id}', "
            f"'{started.isoformat()}', {n}, {duration_ms:.1f}, '{status}')"
        )
