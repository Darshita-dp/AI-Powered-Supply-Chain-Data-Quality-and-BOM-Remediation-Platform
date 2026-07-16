"""Unit tests for structured logging."""

import json

from bom_guardian.observability.logging import configure_logging, get_logger


def test_logs_are_json_with_context(capsys) -> None:  # type: ignore[no-untyped-def]
    configure_logging("INFO")
    log = get_logger("test-component", pipeline_run_id="run-123")
    log.info("something_happened", records=5)

    out = capsys.readouterr().out.strip().splitlines()[-1]
    payload = json.loads(out)
    assert payload["event"] == "something_happened"
    assert payload["component"] == "test-component"
    assert payload["pipeline_run_id"] == "run-123"
    assert payload["records"] == 5
    assert "timestamp" in payload
