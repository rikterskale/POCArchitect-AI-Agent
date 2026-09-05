import json
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

from pocarchitect.finding_workflow import (
    STEPS,
    Finding,
    FindingStatus,
    WorkflowCommandError,
    WorkflowEngine,
    WorkflowError,
    WorkflowPhase,
    WorkflowState,
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


def test_false_positive_can_be_waived_without_stranding_closure():
    engine = WorkflowEngine()
    finding = engine.inject_finding(title="False positive", severity=7)

    with pytest.raises(WorkflowError, match="non-empty rationale"):
        engine.waive_finding(finding.id, rationale=" ")

    engine.waive_finding(finding.id, rationale="Reproduced as a test-only asset")
    assert finding.status == FindingStatus.WAIVED
    assert finding.id not in engine.state.open_findings
    assert engine.state.pending_actions[f"validate:{finding.id}"].status == "done"
    assert any(event["event"] == "finding.waived" for event in engine.state.audit_log)

    engine.decide("scope_defined", True)
    engine.complete_step("scope")
    engine.decide("authorized", True)
    engine.complete_step("authorize")
    engine.complete_step("discover")
    engine.complete_step("validate")
    engine.complete_step("assess-impact")
    engine.complete_step("plan-remediation")
    engine.complete_step("verify-remediation")
    engine.complete_step("report")
    engine.decide("closure_approved", True)
    engine.complete_step("close")
    engine.complete_step("archive")
    assert engine.state.terminal is True


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


def test_initial_read_model_is_consistent_and_scope_can_be_confirmed_later():
    engine = WorkflowEngine()
    assert engine.state.current_phase == WorkflowPhase.SCOPE
    assert engine.state.current_step_id == "scope"
    engine.complete_step("scope")
    with pytest.raises(WorkflowError, match="authorized"):
        engine.complete_step("authorize")


def test_enrichment_updates_scores_and_rejects_invalid_payload_without_partial_update():
    engine = WorkflowEngine()
    finding = engine.add_finding(title="Observation", severity=2, confidence=50)
    with pytest.raises(WorkflowError, match="severity"):
        engine.enrich_finding(finding.id, evidence=["evidence-a"], severity=11)
    assert finding.evidence == []
    engine.enrich_finding(
        finding.id,
        evidence=["evidence-a"],
        severity=8,
        confidence=100,
        recommended_actions=["rotate credential"],
        metadata={"asset": "api"},
    )
    assert engine.state.risk_score == 8.0
    assert finding.recommended_actions == ["rotate credential"]
    assert finding.metadata["asset"] == "api"


def test_late_finding_reopens_report_route_and_requires_closure_approval():
    engine = WorkflowEngine()
    engine.decide("scope_defined", True)
    engine.complete_step("scope")
    engine.decide("authorized", True)
    engine.complete_step("authorize")
    engine.complete_step("discover")
    engine.complete_step("report")
    assert engine.state.current_step_id == "close"
    finding = engine.inject_finding(title="Late observation", severity=5)
    assert finding.id in engine.state.open_findings
    assert engine.state.current_step_id == "validate"
    assert any("closure_approved" in item for item in engine.blockers("close"))


def test_query_rejects_invalid_filters():
    engine = WorkflowEngine()
    with pytest.raises(WorkflowError, match="Unknown finding status"):
        engine.query_findings(status="invalid")
    with pytest.raises(WorkflowError, match="Minimum"):
        engine.query_findings(min_severity=11)


def test_command_boundary_and_preflight_gate_are_ui_agent_safe():
    engine = WorkflowEngine()
    gate = engine.can_complete("authorize")
    assert gate["allowed"] is False
    assert "Current step" in gate["blockers"][0]

    engine.apply("decide", key="scope_defined", value=True)
    engine.apply("complete_step", step_id="scope")
    engine.apply("decide", key="authorized", value=True)
    assert engine.next_recommendation()["step_id"] == "authorize"
    with pytest.raises(WorkflowCommandError, match="Unsupported"):
        engine.apply("not-a-command")


def test_integrity_check_detects_corrupt_references_without_mutation():
    engine = WorkflowEngine()
    finding = engine.add_finding(title="Observation")
    finding.related_finding_ids.append("missing")
    errors = engine.validate_integrity()
    assert "unknown related finding: missing" in errors
    assert finding.related_finding_ids == ["missing"]


def test_historical_override_does_not_rewind_guided_route():
    engine = WorkflowEngine()
    engine.decide("scope_defined", True)
    engine.complete_step("scope")
    engine.decide("authorized", True)
    engine.complete_step("authorize")

    assert engine.state.current_step_id == "discover"
    engine.complete_step(
        "scope", override=True, rationale="Backfilled owner confirmation"
    )
    assert engine.state.current_step_id == "discover"


def test_snapshot_contains_durable_guidance_context_without_shared_mutables():
    engine = WorkflowEngine()
    finding = engine.inject_finding(
        title="Contextual observation", severity=7, recommended_actions=["triage"]
    )
    snapshot = engine.snapshot()

    assert snapshot["findings"][finding.id]["status"] == "open"
    assert snapshot["findings"][finding.id]["recommended_actions"] == ["triage"]
    assert snapshot["actions"][f"validate:{finding.id}"]["status"] == "pending"
    snapshot["findings"][finding.id]["recommended_actions"].append("mutated")
    assert finding.recommended_actions == ["triage"]


def test_query_findings_returns_defensive_copies():
    engine = WorkflowEngine()
    finding = engine.inject_finding(title="Read model safety", tags=["api"])

    result = engine.query_findings(tag="api")
    result[0].tags.append("mutated")
    result[0].severity = 10

    assert finding.tags == ["api"]
    assert finding.severity == 0


def test_command_boundary_rolls_back_failed_mutation():
    engine = WorkflowEngine()
    finding = engine.inject_finding(title="Atomic command")
    before = engine.snapshot()

    with pytest.raises(WorkflowError, match="severity"):
        engine.apply(
            "enrich_finding",
            finding_id=finding.id,
            evidence=["must-rollback"],
            severity=11,
        )

    assert engine.snapshot() == before


def test_custom_route_without_validation_has_no_report_dead_end():
    from pocarchitect.finding_workflow import STEPS

    route = tuple(step for step in STEPS if step.id != "validate")
    engine = WorkflowEngine(steps=route)
    engine.decide("scope_defined", True)
    engine.complete_step("scope")
    engine.decide("authorized", True)
    engine.complete_step("authorize")
    engine.inject_finding(title="Custom route observation")
    engine.complete_step("discover")
    engine.complete_step("assess-impact")
    engine.complete_step("plan-remediation")
    engine.complete_step("verify-remediation")
    assert engine.state.current_step_id == "report"
    assert engine.can_complete("report")["allowed"] is True


def test_workflow_loader_rejects_unknown_schema(tmp_path):
    path = tmp_path / "workflow.json"
    path.write_text(json.dumps({"version": 1}), encoding="utf-8")
    with pytest.raises(WorkflowError, match="Unsupported workflow schema"):
        WorkflowEngine.load(path)


def test_workflow_save_cleans_temporary_file_after_serialization_error(tmp_path):
    engine = WorkflowEngine()
    engine.state.metadata["not-json"] = object()
    path = tmp_path / "workflow.json"

    with pytest.raises(TypeError):
        engine.save(path)

    assert not path.exists()
    assert list(tmp_path.glob(".workflow.json.*.tmp")) == []


def test_finding_and_custom_route_validation_errors():
    with pytest.raises(WorkflowError, match="title is required"):
        Finding(title=" ")
    with pytest.raises(WorkflowError, match="severity"):
        Finding(title="bad", severity=11)
    with pytest.raises(WorkflowError, match="Unknown finding status"):
        Finding(title="bad", status="unknown")
    with pytest.raises(WorkflowError, match="one or more uniquely"):
        WorkflowEngine(steps=())
    with pytest.raises(WorkflowError, match="one or more uniquely"):
        WorkflowEngine(steps=(STEPS[0], STEPS[0]))
    with pytest.raises(WorkflowError, match="title and explanation"):
        WorkflowEngine(steps=(replace(STEPS[0], title=""), STEPS[-1]))
    with pytest.raises(WorkflowError, match="end with the archive"):
        WorkflowEngine(steps=STEPS[:-1])
    with pytest.raises(WorkflowError, match="archived phase"):
        WorkflowEngine(
            steps=(*STEPS[:-1], replace(STEPS[-1], phase=WorkflowPhase.REPORTING))
        )
    with pytest.raises(WorkflowError, match="current_phase"):
        WorkflowEngine(WorkflowState(current_phase=WorkflowPhase.REPORTING))
    with pytest.raises(WorkflowError, match="positioned at archive"):
        WorkflowEngine(WorkflowState(terminal=True))
    with pytest.raises(WorkflowError, match="Unknown current workflow step"):
        WorkflowEngine(WorkflowState(current_step_id="missing"))


def test_workflow_public_mutation_and_integrity_error_paths(tmp_path):
    engine = WorkflowEngine()
    finding = engine.add_finding(title="one")
    with pytest.raises(WorkflowError, match="already exists"):
        engine.add_finding(finding)
    with pytest.raises(WorkflowError, match="confidence"):
        engine.enrich_finding(finding.id, confidence=101)
    with pytest.raises(WorkflowError, match="Decision key"):
        engine.decide(" ", True)
    with pytest.raises(WorkflowError, match="Unknown finding"):
        engine.correlate(finding.id, ["missing"])
    with pytest.raises(WorkflowError, match="Unknown action"):
        engine.resolve_action("missing")

    action_id = f"validate:{finding.id}"
    engine.resolve_action(action_id)
    engine.resolve_action(action_id)
    assert engine.state.pending_actions[action_id].status == "done"

    engine.state.completed_steps.append("missing-step")
    finding_key = finding.id
    engine.state.findings[finding_key].id = "different"
    engine.state.findings[finding_key].related_finding_ids = ["missing"]
    engine.state.pending_actions[action_id].id = "different-action"
    engine.state.pending_actions[action_id].finding_id = "missing"
    errors = engine.validate_integrity()
    assert len(errors) >= 5
    with pytest.raises(WorkflowError, match="Cannot persist invalid"):
        engine.save(tmp_path / "invalid.json")


def test_workflow_loader_wraps_invalid_json_and_invalid_integrity(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text("not json", encoding="utf-8")
    with pytest.raises(WorkflowError, match="Cannot load"):
        WorkflowEngine.load(broken)

    engine = WorkflowEngine()
    path = tmp_path / "workflow.json"
    engine.save(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["completed_steps"] = ["missing"]
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(WorkflowError, match="Invalid workflow state"):
        WorkflowEngine.load(path)


def test_correlate_links_findings_and_apply_rejects_invalid_payload():
    engine = WorkflowEngine()
    first = engine.add_finding(title="One", severity=4)
    second = engine.add_finding(title="Two", severity=5)

    linked = engine.correlate(first.id, [second.id, first.id, second.id])

    assert linked.related_finding_ids == [second.id]
    assert engine.state.findings[first.id].related_finding_ids == [second.id]

    before = engine.snapshot()
    with pytest.raises(WorkflowCommandError, match="Invalid payload"):
        engine.apply("decide", unexpected=True)
    assert engine.snapshot() == before


def test_blockers_cover_scope_validation_actions_and_closure():
    engine = WorkflowEngine()
    assert engine.blockers("discover") == ["Record a scope_defined=true decision."]

    engine.decide("scope_defined", True)
    engine.complete_step("scope")
    engine.decide("authorized", True)
    engine.complete_step("authorize")
    finding = engine.add_finding(title="Open observation", severity=8, confidence=80)
    engine.complete_step("discover")
    assert engine.blockers("validate") == [
        "Validate or explicitly reject every open finding."
    ]
    assert engine.blockers("assess-impact") == [
        "Validate all open findings before continuing."
    ]

    engine.update_finding_status(finding.id, FindingStatus.VALIDATED)
    engine.complete_step("validate")
    assert "Resolve required finding actions" in engine.blockers("plan-remediation")[0]
    engine.resolve_action(f"impact:{finding.id}")
    engine.complete_step("assess-impact")
    assert (
        "Resolve required finding actions" in engine.blockers("verify-remediation")[0]
    )

    engine.resolve_action(f"remediate:{finding.id}")
    engine.update_finding_status(finding.id, FindingStatus.MITIGATED)
    engine.complete_step("plan-remediation")
    engine.complete_step("verify-remediation")
    engine.complete_step("report")
    engine.decide("closure_approved", True)
    assert engine.blockers("close") == ["Complete all required pending actions."]

    engine.resolve_action(f"verify:{finding.id}")
    assert engine.blockers("close") == ["Close or explicitly waive every finding."]


def test_archived_workflow_recommends_completion():
    engine = WorkflowEngine()
    engine.decide("scope_defined", True)
    engine.complete_step("scope")
    engine.decide("authorized", True)
    engine.complete_step("authorize")
    engine.complete_step("discover")
    engine.complete_step("report")
    engine.complete_step("close")
    engine.complete_step("archive")

    assert engine.state.terminal is True
    kinds = [item["kind"] for item in engine.recommendations()]
    assert "complete" in kinds
    assert "step" not in kinds
    assert engine.next_recommendation()["kind"] == "complete"
    assert engine.next_recommendation()["title"] == "No action is pending."
