from pathlib import Path
from uuid import uuid4

import pytest

from pocarchitect.finding_workflow import (
    Finding,
    FindingStatus,
    WorkflowEngine,
    WorkflowError,
    WorkflowPhase,
)


def test_finding_drives_actions_risk_and_query():
    engine = WorkflowEngine()
    finding = engine.add_finding(
        title="Exposed service", severity=8, confidence=75, tags=["network"]
    )

    assert engine.state.risk_score == 6.0
    assert engine.state.pending_actions[f"validate:{finding.id}"].required
    assert engine.query_findings(min_severity=7, tag="network")[0].id == finding.id
    assert engine.recommendations()[0]["kind"] == "step"


def test_gates_and_full_lifecycle_are_resumable():
    engine = WorkflowEngine()
    engine.decide("scope_defined", True)
    engine.complete_step("scope")
    with pytest.raises(WorkflowError):
        engine.complete_step("authorize")
    engine.decide("authorized", True)
    engine.complete_step("authorize")
    finding = engine.add_finding(title="Injection", severity=9, confidence=90)
    engine.complete_step("discover")
    engine.update_finding_status(finding.id, FindingStatus.VALIDATED)
    engine.update_finding_status(finding.id, FindingStatus.EXPLOITED)
    engine.update_finding_status(finding.id, FindingStatus.MITIGATED)
    engine.update_finding_status(finding.id, FindingStatus.CLOSED)
    assert finding.history[-1]["from"] == "mitigated"

    path = Path(f".workflow-test-{uuid4().hex}.json")
    try:
        engine.save(path)
        resumed = WorkflowEngine.load(path)
        assert resumed.state.current_phase == WorkflowPhase.VALIDATION
        assert resumed.state.findings[finding.id].status == FindingStatus.CLOSED
        assert resumed.state.audit_log
    finally:
        path.unlink(missing_ok=True)


def test_invalid_lifecycle_and_unknown_references_fail_safely():
    engine = WorkflowEngine()
    finding = engine.add_finding(title="Observation")
    with pytest.raises(WorkflowError):
        engine.update_finding_status(finding.id, FindingStatus.CLOSED)
    with pytest.raises(WorkflowError):
        engine.correlate(finding.id, ["missing"])
    with pytest.raises(WorkflowError):
        engine.resolve_action("missing")


def test_override_and_agent_mode_are_audited():
    engine = WorkflowEngine()
    engine.state.mode = "automated"
    engine.add_finding(Finding(title="Injected by agent", source="agent"))
    next_step = engine.complete_step(
        "scope", override=True, rationale="Approved exception from orchestrator"
    )
    assert next_step == "authorize"
    assert engine.state.audit_log[-1]["override"] is True


def test_empty_scope_takes_a_safe_branch_to_report_and_archive():
    engine = WorkflowEngine()
    engine.decide("scope_defined", True)
    engine.complete_step("scope")
    engine.decide("authorized", True)
    engine.complete_step("authorize")
    assert engine.complete_step("discover") == "report"
    assert {
        "validate",
        "assess-impact",
        "plan-remediation",
        "verify-remediation",
    }.issubset(set(engine.state.skipped_steps))
    engine.complete_step("report")
    engine.complete_step("close")
    engine.complete_step("archive")
    assert engine.state.terminal is True
    assert engine.state.progress_percent == 100.0


def test_finding_actions_reconcile_with_lifecycle_and_priority():
    engine = WorkflowEngine()
    finding = engine.inject_finding(
        title="Confirmed injection", severity=8, confidence=80, source="scanner"
    )
    assert engine.state.priority_score == 6.4
    assert engine.state.pending_actions[f"validate:{finding.id}"].status == "pending"

    engine.update_finding_status(finding.id, FindingStatus.VALIDATED)
    assert engine.state.pending_actions[f"validate:{finding.id}"].status == "done"
    assert engine.state.pending_actions[f"impact:{finding.id}"].status == "pending"
    assert engine.state.pending_actions[f"remediate:{finding.id}"].status == "pending"

    engine.resolve_action(f"impact:{finding.id}")
    engine.update_finding_status(finding.id, FindingStatus.MITIGATED)
    assert engine.state.pending_actions[f"remediate:{finding.id}"].status == "done"
    assert engine.state.pending_actions[f"verify:{finding.id}"].status == "pending"
    engine.resolve_action(f"verify:{finding.id}")
    engine.update_finding_status(finding.id, FindingStatus.CLOSED)
    assert engine.state.priority_score == 0.0


def test_override_requires_explanation_and_progress_is_recommendable():
    engine = WorkflowEngine()
    with pytest.raises(WorkflowError, match="rationale"):
        engine.complete_step("scope", override=True)
    assert any(item["kind"] == "progress" for item in engine.recommendations())


def test_snapshot_is_a_complete_guidance_read_model():
    engine = WorkflowEngine()
    finding = engine.inject_finding(
        title="User observation", severity=6, confidence=100
    )

    snapshot = engine.snapshot()

    assert snapshot["workflow_id"] == engine.state.id
    assert finding.id in snapshot["open_findings"]
    assert f"validate:{finding.id}" in snapshot["pending_actions"]
    assert snapshot["recommendations"]
    assert snapshot["terminal"] is False


def test_archive_is_idempotently_terminal_and_rejects_future_mutation():
    engine = WorkflowEngine()
    engine.state.completed_steps = [step.id for step in engine.steps[:-1]]
    engine.state.current_step_id = "archive"
    engine.state.current_phase = WorkflowPhase.ARCHIVED

    engine.complete_step("archive")
    assert engine.state.terminal is True
    assert engine.state.progress_percent == 100.0
    engine.complete_step("archive")
    with pytest.raises(WorkflowError, match="archived"):
        engine.complete_step("report", override=True, rationale="late edit")


def test_invalid_status_is_reported_as_workflow_error():
    engine = WorkflowEngine()
    finding = engine.add_finding(title="Malformed input")

    with pytest.raises(WorkflowError, match="Unknown finding status"):
        engine.update_finding_status(finding.id, "not-a-status")
