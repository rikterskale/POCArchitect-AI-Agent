"""Finding-driven, resumable guided workflow engine.

The module is deliberately UI-agnostic: a CLI, web UI, or agent can render
``recommendations()`` and submit the returned commands through the same API.
All mutations are event-audited and the state is safe to persist as JSON.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorkflowError(ValueError):
    """Invalid command, transition, or persisted workflow state."""


class FindingStatus(str, Enum):
    OPEN = "open"
    VALIDATED = "validated"
    EXPLOITED = "exploited"
    MITIGATED = "mitigated"
    CLOSED = "closed"


class WorkflowPhase(str, Enum):
    INTAKE = "intake"
    SCOPE = "scope"
    AUTHORIZATION = "authorization"
    DISCOVERY = "discovery"
    VALIDATION = "validation"
    IMPACT = "impact"
    REMEDIATION = "remediation"
    REPORTING = "reporting"
    CLOSURE = "closure"
    ARCHIVED = "archived"


@dataclass
class Finding:
    """A durable observation and the evidence/decisions derived from it."""

    title: str
    description: str = ""
    severity: int = 0  # 0-10; normalized rather than tied to a vendor scale
    confidence: int = 50  # 0-100
    source: str = "user"
    id: str = field(default_factory=lambda: f"finding-{uuid.uuid4().hex[:12]}")
    status: FindingStatus = FindingStatus.OPEN
    tags: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    related_finding_ids: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    history: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.title, str) or not self.title.strip():
            raise WorkflowError("Finding title is required")
        if not 0 <= self.severity <= 10 or not 0 <= self.confidence <= 100:
            raise WorkflowError("Finding severity must be 0-10 and confidence 0-100")
        try:
            self.status = FindingStatus(self.status)
        except ValueError as exc:
            raise WorkflowError(f"Unknown finding status: {self.status}") from exc


@dataclass
class PendingAction:
    id: str
    title: str
    kind: str
    finding_id: str | None = None
    required: bool = True
    status: str = "pending"
    rationale: str = ""


@dataclass
class WorkflowState:
    """Complete snapshot needed to resume and explain a workflow."""

    id: str = field(default_factory=lambda: f"workflow-{uuid.uuid4().hex[:12]}")
    version: int = 1
    # ``scope`` is the first actionable step.  Keeping the phase aligned with
    # it avoids an impossible initial read-model (intake + scope).
    current_phase: WorkflowPhase = WorkflowPhase.SCOPE
    current_step_id: str = "scope"
    completed_steps: list[str] = field(default_factory=list)
    skipped_steps: list[str] = field(default_factory=list)
    findings: dict[str, Finding] = field(default_factory=dict)
    pending_actions: dict[str, PendingAction] = field(default_factory=dict)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    audit_log: list[dict[str, Any]] = field(default_factory=list)
    progress_percent: float = 0.0
    risk_score: float = 0.0
    priority_score: float = 0.0
    mode: str = "interactive"
    terminal: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def open_findings(self) -> list[str]:
        """IDs of findings that still require a decision or treatment."""
        return [
            finding_id
            for finding_id, finding in self.findings.items()
            if finding.status != FindingStatus.CLOSED
        ]

    @property
    def open_actions(self) -> list[str]:
        """IDs of required actions that have not been resolved."""
        return [
            action_id
            for action_id, action in self.pending_actions.items()
            if action.required and action.status == "pending"
        ]


@dataclass(frozen=True)
class Step:
    id: str
    phase: WorkflowPhase
    title: str
    explanation: str


STEPS: tuple[Step, ...] = (
    Step(
        "scope",
        WorkflowPhase.SCOPE,
        "Define scope",
        "Identify assets, objectives, exclusions, and stakeholders.",
    ),
    Step(
        "authorize",
        WorkflowPhase.AUTHORIZATION,
        "Confirm authorization",
        "Confirm the work is permitted and record its boundaries.",
    ),
    Step(
        "discover",
        WorkflowPhase.DISCOVERY,
        "Collect observations",
        "Gather evidence from approved sources; observations become findings.",
    ),
    Step(
        "validate",
        WorkflowPhase.VALIDATION,
        "Validate findings",
        "Confirm relevance, reproducibility, severity, and confidence.",
    ),
    Step(
        "assess-impact",
        WorkflowPhase.IMPACT,
        "Assess impact",
        "Determine affected assets, business impact, and exploitability.",
    ),
    Step(
        "plan-remediation",
        WorkflowPhase.REMEDIATION,
        "Plan remediation",
        "Create treatment actions for material findings.",
    ),
    Step(
        "verify-remediation",
        WorkflowPhase.REMEDIATION,
        "Verify remediation",
        "Re-test mitigations and update finding lifecycles.",
    ),
    Step(
        "report",
        WorkflowPhase.REPORTING,
        "Prepare final report",
        "Explain scope, evidence, decisions, residual risk, and exceptions.",
    ),
    Step(
        "close",
        WorkflowPhase.CLOSURE,
        "Approve closure",
        "Obtain closure decision and confirm no required work remains.",
    ),
    Step(
        "archive",
        WorkflowPhase.ARCHIVED,
        "Archive record",
        "Freeze the auditable record and mark the workflow complete.",
    ),
)


class WorkflowEngine:
    """Command-style engine for interactive and automated/agent-driven use."""

    def __init__(
        self, state: WorkflowState | None = None, steps: Iterable[Step] = STEPS
    ):
        self.state = state or WorkflowState()
        self.steps = tuple(steps)
        if not self.steps or len({step.id for step in self.steps}) != len(self.steps):
            raise WorkflowError(
                "Workflow must define one or more uniquely identified steps"
            )
        if self.state.current_step_id not in {step.id for step in self.steps}:
            raise WorkflowError(
                f"Unknown current workflow step: {self.state.current_step_id}"
            )
        self._validate_steps()
        self._recalculate()

    def _validate_steps(self) -> None:
        """Reject malformed custom routes before a user can get stranded."""
        if any(not step.title.strip() or not step.explanation.strip() for step in self.steps):
            raise WorkflowError("Every workflow step needs a title and explanation")
        if self.steps[-1].id != "archive":
            raise WorkflowError("Workflow must end with the archive step")
        if self.steps[-1].phase != WorkflowPhase.ARCHIVED:
            raise WorkflowError("Archive step must use the archived phase")

    def _audit(self, event: str, **data: Any) -> None:
        self.state.audit_log.append({"at": _now(), "event": event, **data})

    def _recalculate(self) -> None:
        findings = list(self.state.findings.values())
        self.state.risk_score = round(
            sum(f.severity * (f.confidence / 100) for f in findings), 2
        )
        # Priority weights urgency (severity), certainty (confidence), and
        # exploitability. It is intentionally transparent and replaceable by
        # a policy adapter at the application boundary.
        self.state.priority_score = round(
            sum(
                f.severity
                * (f.confidence / 100)
                * (1.25 if f.status == FindingStatus.EXPLOITED else 1.0)
                for f in findings
                if f.status != FindingStatus.CLOSED
            ),
            2,
        )
        self.state.progress_percent = round(
            100
            * (len(set(self.state.completed_steps) | set(self.state.skipped_steps)))
            / len(self.steps),
            1,
        )
        if self.state.terminal:
            self.state.progress_percent = 100.0
        # Keep derived required actions coherent after every command.
        for finding in findings:
            if finding.status == FindingStatus.OPEN:
                self._ensure_action(
                    f"validate:{finding.id}",
                    "Validate finding",
                    "validate",
                    finding.id,
                    "Open finding requires validation.",
                )
            elif finding.status in (
                FindingStatus.VALIDATED,
                FindingStatus.EXPLOITED,
            ):
                self._ensure_action(
                    f"impact:{finding.id}",
                    "Assess finding impact",
                    "impact",
                    finding.id,
                    "Validated finding needs impact and exploitability assessment.",
                )
                if finding.severity >= 4:
                    self._ensure_action(
                        f"remediate:{finding.id}",
                        "Plan or verify remediation",
                        "remediate",
                        finding.id,
                        "Material finding requires treatment.",
                    )
            elif finding.status == FindingStatus.MITIGATED:
                self._ensure_action(
                    f"verify:{finding.id}",
                    "Verify remediation",
                    "verify",
                    finding.id,
                    "Mitigated finding requires verification before closure.",
                )
        # Lifecycle changes make earlier derived actions obsolete. Mark them
        # done rather than deleting them, preserving the audit-friendly trail.
        for action in self.state.pending_actions.values():
            if action.finding_id and action.finding_id in self.state.findings:
                status = self.state.findings[action.finding_id].status
                obsolete = (
                    (action.kind == "validate" and status != FindingStatus.OPEN)
                    or (
                        action.kind == "impact"
                        and status
                        not in (FindingStatus.VALIDATED, FindingStatus.EXPLOITED)
                    )
                    or (
                        action.kind == "remediate"
                        and status in (FindingStatus.MITIGATED, FindingStatus.CLOSED)
                    )
                    or (action.kind == "verify" and status == FindingStatus.CLOSED)
                )
                if obsolete:
                    action.status = "done"
        for action_id, action in list(self.state.pending_actions.items()):
            if action.finding_id and action.finding_id not in self.state.findings:
                del self.state.pending_actions[action_id]

    def _ensure_action(
        self, action_id: str, title: str, kind: str, finding_id: str, rationale: str
    ) -> None:
        if action_id not in self.state.pending_actions:
            self.state.pending_actions[action_id] = PendingAction(
                action_id, title, kind, finding_id, True, "pending", rationale
            )

    def _step(self, step_id: str) -> Step:
        try:
            return next(step for step in self.steps if step.id == step_id)
        except StopIteration as exc:
            raise WorkflowError(f"Unknown workflow step: {step_id}") from exc

    def add_finding(self, finding: Finding | None = None, **values: Any) -> Finding:
        if self.state.terminal:
            raise WorkflowError("Workflow is archived and cannot accept findings")
        finding = finding or Finding(**values)
        if finding.id in self.state.findings:
            raise WorkflowError(f"Finding already exists: {finding.id}")
        self.state.findings[finding.id] = finding
        self._audit(
            "finding.created",
            finding_id=finding.id,
            title=finding.title,
            source=finding.source,
        )
        self._reopen_for_new_finding()
        self._recalculate()
        return finding

    def enrich_finding(
        self,
        finding_id: str,
        *,
        evidence: Iterable[str] = (),
        tags: Iterable[str] = (),
        description: str | None = None,
        severity: int | None = None,
        confidence: int | None = None,
        recommended_actions: Iterable[str] = (),
        metadata: dict[str, Any] | None = None,
    ) -> Finding:
        finding = self._finding(finding_id)
        if severity is not None and not 0 <= severity <= 10:
            raise WorkflowError("Finding severity must be 0-10")
        if confidence is not None and not 0 <= confidence <= 100:
            raise WorkflowError("Finding confidence must be 0-100")
        # Validate all scalar updates before changing any collection so a bad
        # connector payload cannot leave a half-enriched finding behind.
        finding.evidence.extend(x for x in evidence if x not in finding.evidence)
        finding.tags.extend(x for x in tags if x not in finding.tags)
        if description is not None:
            finding.description = description
        if severity is not None:
            finding.severity = severity
        if confidence is not None:
            finding.confidence = confidence
        finding.recommended_actions.extend(
            x for x in recommended_actions if x not in finding.recommended_actions
        )
        if metadata:
            finding.metadata.update(metadata)
        finding.updated_at = _now()
        finding.history.append({"at": finding.updated_at, "event": "enriched"})
        self._audit("finding.enriched", finding_id=finding_id)
        self._recalculate()
        return finding

    def inject_finding(self, **values: Any) -> Finding:
        """Explicit entry point for user, connector, or agent observations."""
        values.setdefault("source", "injected")
        return self.add_finding(**values)

    def update_finding_status(
        self, finding_id: str, status: FindingStatus, *, reason: str = ""
    ) -> Finding:
        finding = self._finding(finding_id)
        try:
            status = FindingStatus(status)
        except ValueError as exc:
            raise WorkflowError(f"Unknown finding status: {status}") from exc
        previous = finding.status
        allowed = {
            FindingStatus.OPEN: {FindingStatus.VALIDATED},
            FindingStatus.VALIDATED: {FindingStatus.EXPLOITED, FindingStatus.MITIGATED},
            FindingStatus.EXPLOITED: {FindingStatus.MITIGATED},
            FindingStatus.MITIGATED: {FindingStatus.CLOSED},
            FindingStatus.CLOSED: set(),
        }
        if status != finding.status and status not in allowed[finding.status]:
            raise WorkflowError(
                f"Invalid finding transition {finding.status.value} -> {status.value}"
            )
        finding.status = status
        finding.updated_at = _now()
        finding.history.append(
            {
                "at": finding.updated_at,
                "event": "status.changed",
                "from": previous.value,
                "to": status.value,
                "reason": reason,
            }
        )
        self._audit(
            "finding.status_changed",
            finding_id=finding_id,
            status=status.value,
            reason=reason,
        )
        self._recalculate()
        return finding

    def decide(self, key: str, value: Any, *, rationale: str = "") -> None:
        if not key.strip():
            raise WorkflowError("Decision key is required")
        self.state.decisions.append(
            {"key": key, "value": value, "rationale": rationale, "at": _now()}
        )
        self._audit("decision.recorded", key=key, value=value, rationale=rationale)
        self._recalculate()

    def correlate(self, finding_id: str, related_finding_ids: Iterable[str]) -> Finding:
        finding = self._finding(finding_id)
        related = list(dict.fromkeys(related_finding_ids))
        for related_id in related:
            self._finding(related_id)
        finding.related_finding_ids = [item for item in related if item != finding_id]
        finding.updated_at = _now()
        self._audit(
            "finding.correlated",
            finding_id=finding_id,
            related_finding_ids=finding.related_finding_ids,
        )
        self._recalculate()
        return finding

    def resolve_action(self, action_id: str, *, note: str = "") -> None:
        action = self.state.pending_actions.get(action_id)
        if action is None:
            raise WorkflowError(f"Unknown action: {action_id}")
        if action.status == "done":
            return
        action.status = "done"
        self._audit("action.completed", action_id=action_id, note=note)
        self._recalculate()

    def complete_step(
        self, step_id: str | None = None, *, override: bool = False, rationale: str = ""
    ) -> str:
        step_id = step_id or self.state.current_step_id
        self._step(step_id)
        if self.state.terminal and step_id != "archive":
            raise WorkflowError("Workflow is archived and cannot accept more steps")
        if step_id in self.state.completed_steps:
            if step_id == "archive":
                self.state.terminal = True
                self.state.current_phase = WorkflowPhase.ARCHIVED
                self._recalculate()
            return self.state.current_step_id
        if step_id != self.state.current_step_id and not override:
            raise WorkflowError(
                f"Current step is {self.state.current_step_id}; use override for out-of-order completion"
            )
        blockers = self.blockers(step_id)
        if blockers and not override:
            raise WorkflowError("Step is blocked: " + "; ".join(blockers))
        if override and not rationale.strip():
            raise WorkflowError("An override requires a non-empty rationale")
        self.state.completed_steps.append(step_id)
        self._audit(
            "step.completed", step_id=step_id, override=override, rationale=rationale
        )
        next_id = self._next_step(step_id)
        while next_id != step_id and self._should_skip(next_id):
            if next_id not in self.state.skipped_steps:
                self.state.skipped_steps.append(next_id)
                self._audit(
                    "step.skipped", step_id=next_id, reason="finding-driven branch"
                )
            next_id = self._next_step(next_id)
        self.state.current_step_id = next_id
        self.state.current_phase = self._step(next_id).phase
        self.state.terminal = step_id == "archive"
        if self.state.terminal:
            self.state.current_step_id = "archive"
            self.state.current_phase = WorkflowPhase.ARCHIVED
        self._recalculate()
        return next_id

    def _reopen_for_new_finding(self) -> None:
        """Re-enter finding work when a late observation changes the route.

        This is deliberately conservative: an archived record is immutable,
        while a non-terminal report/closure route can be reopened and audited.
        The previously completed report remains historical; the route will
        return to it after the new finding is treated.
        """
        if self.state.terminal:
            return
        if self.state.current_step_id in {"report", "close"}:
            previous = self.state.current_step_id
            self.state.current_step_id = "validate"
            self.state.current_phase = self._step("validate").phase
            self._audit(
                "workflow.reopened",
                reason="new finding requires treatment",
                from_step=previous,
                to_step="validate",
            )

    def _next_step(self, step_id: str) -> str:
        index = next(i for i, step in enumerate(self.steps) if step.id == step_id)
        return self.steps[min(index + 1, len(self.steps) - 1)].id

    def _should_skip(self, step_id: str) -> bool:
        """Branch low-signal workflows while retaining a complete report route."""
        if self.state.findings:
            return False
        return step_id in {
            "validate",
            "assess-impact",
            "plan-remediation",
            "verify-remediation",
        }

    def blockers(self, step_id: str | None = None) -> list[str]:
        step_id = step_id or self.state.current_step_id
        if step_id == "authorize" and not self._decision("authorized"):
            return ["Record an authorized=true decision."]
        if step_id == "discover" and not self._decision("scope_defined"):
            return ["Record a scope_defined=true decision."]
        if step_id == "validate" and any(
            f.status == FindingStatus.OPEN for f in self.state.findings.values()
        ):
            return ["Validate or explicitly reject every open finding."]
        if step_id in {
            "assess-impact",
            "plan-remediation",
            "verify-remediation",
            "report",
        } and any(f.status == FindingStatus.OPEN for f in self.state.findings.values()):
            return ["Validate all open findings before continuing."]
        if step_id == "plan-remediation":
            incomplete = [
                a.title
                for a in self.state.pending_actions.values()
                if a.required and a.status != "done" and a.kind == "impact"
            ]
            if incomplete:
                return ["Resolve required finding actions: " + ", ".join(incomplete)]
        if step_id == "verify-remediation":
            incomplete = [
                a.title
                for a in self.state.pending_actions.values()
                if a.required and a.status != "done" and a.kind == "remediate"
            ]
            if incomplete:
                return ["Resolve required finding actions: " + ", ".join(incomplete)]
        if step_id == "close":
            # A no-finding assessment has no residual risk to approve.  A
            # finding-bearing workflow always requires an explicit closure
            # decision, including the rationale captured in its history.
            if self.state.findings and not self._decision("closure_approved"):
                return ["Record a closure_approved=true decision."]
            if any(
                a.required and a.status != "done"
                for a in self.state.pending_actions.values()
            ):
                return ["Complete all required pending actions."]
            if any(
                f.status != FindingStatus.CLOSED for f in self.state.findings.values()
            ):
                return ["Close or explicitly waive every finding."]
        return []

    def _decision(self, key: str) -> bool:
        # Decisions are historical, but the latest one is authoritative.  This
        # allows a user to correct a prior choice without corrupting the audit.
        for decision in reversed(self.state.decisions):
            if decision.get("key") == key:
                return decision.get("value") is True
        return False

    def _finding(self, finding_id: str) -> Finding:
        if finding_id not in self.state.findings:
            raise WorkflowError(f"Unknown finding: {finding_id}")
        return self.state.findings[finding_id]

    def recommendations(self) -> list[dict[str, Any]]:
        step = self._step(self.state.current_step_id)
        blockers = self.blockers(step.id)
        result = [
            {"kind": "blocker", "title": text, "required": True} for text in blockers
        ]
        if not blockers:
            result.append(
                {
                    "kind": "step",
                    "step_id": step.id,
                    "title": step.title,
                    "explanation": step.explanation,
                    "required": True,
                }
            )
        for action in self.state.pending_actions.values():
            if action.status == "pending":
                result.append({"kind": action.kind, **asdict(action)})
        if self.state.findings:
            for finding in sorted(
                self.state.findings.values(),
                key=lambda item: (item.status == FindingStatus.CLOSED, -item.severity),
            ):
                if finding.status != FindingStatus.CLOSED:
                    result.append(
                        {
                            "kind": "finding",
                            "finding_id": finding.id,
                            "title": finding.title,
                            "status": finding.status.value,
                            "severity": finding.severity,
                            "confidence": finding.confidence,
                            "next": self._finding_next_action(finding),
                        }
                    )
        result.append(
            {
                "kind": "progress",
                "phase": self.state.current_phase.value,
                "step_id": self.state.current_step_id,
                "percent": self.state.progress_percent,
                "risk_score": self.state.risk_score,
                "priority_score": self.state.priority_score,
            }
        )
        if not result:
            result.append({"kind": "complete", "title": "No action is pending."})
        return result

    def _finding_next_action(self, finding: Finding) -> str:
        return {
            FindingStatus.OPEN: "validate",
            FindingStatus.VALIDATED: "assess-impact",
            FindingStatus.EXPLOITED: "plan-remediation",
            FindingStatus.MITIGATED: "verify-remediation",
            FindingStatus.CLOSED: "none",
        }[finding.status]

    def snapshot(self) -> dict[str, Any]:
        """Return a UI/agent-safe read model without exposing mutable objects."""
        return {
            "workflow_id": self.state.id,
            "phase": self.state.current_phase.value,
            "step_id": self.state.current_step_id,
            "completed_steps": list(self.state.completed_steps),
            "skipped_steps": list(self.state.skipped_steps),
            "open_findings": self.state.open_findings,
            "pending_actions": self.state.open_actions,
            "progress_percent": self.state.progress_percent,
            "risk_score": self.state.risk_score,
            "priority_score": self.state.priority_score,
            "terminal": self.state.terminal,
            "recommendations": self.recommendations(),
        }

    def query_findings(
        self,
        *,
        status: FindingStatus | None = None,
        min_severity: int = 0,
        tag: str | None = None,
    ) -> list[Finding]:
        try:
            normalized_status = None if status is None else FindingStatus(status)
        except ValueError as exc:
            raise WorkflowError(f"Unknown finding status: {status}") from exc
        if not 0 <= min_severity <= 10:
            raise WorkflowError("Minimum finding severity must be 0-10")
        return [
            f
            for f in self.state.findings.values()
            if (normalized_status is None or f.status == normalized_status)
            and f.severity >= min_severity
            and (tag is None or tag in f.tags)
        ]

    def save(self, path: Path) -> None:
        payload = asdict(self.state)
        payload["current_phase"] = self.state.current_phase.value
        payload["findings"] = {
            key: {**asdict(value), "status": value.status.value}
            for key, value in self.state.findings.items()
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as tmp:
            json.dump(payload, tmp, indent=2, sort_keys=True)
            tmp.write("\n")
            temporary = Path(tmp.name)
        try:
            os.replace(temporary, path)
        except OSError:
            temporary.unlink(missing_ok=True)
            raise

    @classmethod
    def load(cls, path: Path) -> WorkflowEngine:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            findings = {
                key: Finding(**value)
                for key, value in payload.pop("findings", {}).items()
            }
            actions = {
                key: PendingAction(**value)
                for key, value in payload.pop("pending_actions", {}).items()
            }
            payload["current_phase"] = WorkflowPhase(payload["current_phase"])
            payload.setdefault("skipped_steps", [])
            payload.setdefault("priority_score", 0.0)
            state = WorkflowState(**payload, findings=findings, pending_actions=actions)
            return cls(state)
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise WorkflowError(f"Cannot load workflow state: {path}") from exc
