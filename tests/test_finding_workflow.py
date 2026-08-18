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
