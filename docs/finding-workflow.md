# Finding-driven guided workflow

`pocarchitect.finding_workflow` is a UI-agnostic workflow kernel. A client renders the current step, `blockers()`, and `recommendations()`, then sends commands back to the engine. The same commands work for a person, an automation, or an agent.

## Architecture and model

`WorkflowState` is the complete resumable snapshot: current phase and step, completed and skipped steps, findings, pending actions, decisions, audit log, derived risk and priority, progress, mode, metadata, and terminal state. It contains no callbacks, so it can be serialized to JSON and stored behind a repository, API, or event-sourced projection. `skipped_steps` makes dynamic branches explicit instead of hiding them from progress calculations.

`Finding` is a first-class object with identity, description, evidence, source, confidence, severity, tags, correlations, recommended actions, extensible metadata, lifecycle history, and the status lifecycle:

```text
open -> validated -> exploited -> mitigated -> closed
                    \-> mitigated
```

Invalid status transitions are rejected. External observations are injected with `add_finding` or `inject_finding`; `enrich_finding` and `correlate` preserve the finding identity while improving context. Every mutation emits an audit event.

## Engine behavior

The default route is:

```text
scope -> authorize -> discover -> validate -> assess-impact
 -> plan-remediation -> verify-remediation -> report -> close -> archive
```

The route is linear by default, but findings create dynamic gates and actions. Open findings block impact, remediation, verification, and reporting until validated. Material validated/exploited findings (severity >= 4) produce a required remediation action. Closure requires every required action to be done and every finding to be closed. A documented `override=True` is available for emergency, legal, or policy exceptions and is always recorded in the audit log.

Risk is a transparent derived score: `sum(severity * confidence / 100)`. Priority uses the same weighted value and adds a 1.25 exploitability multiplier for non-closed exploited findings. Clients can replace these formulas with a policy adapter while keeping the state contract. `query_findings` supports status, severity, and tag filters.

## Guided client loop

1. Create `WorkflowEngine()` and render the current `Step` explanation and progress percentage.
2. Render `recommendations()`. Show blockers as mandatory, finding actions as contextual, and the current step as the primary call to action.
3. Record user decisions with `decide(key, value, rationale=...)`; decision gates currently include authorization and scope confirmation.
4. Convert every observation or agent result to a `Finding`, then enrich, correlate, validate, exploit-test, mitigate, and close it through the lifecycle API.
5. Complete the current step. On a blocked step, show `WorkflowError` and the exact `blockers()` text; there is no silent dead end.
6. Persist after each mutation using `save(path)` and resume with `WorkflowEngine.load(path)`. The atomic replace prevents partial snapshots after interruption.

## Integration contract

An HTTP, CLI, or agent adapter only needs to expose this command/query boundary:

```python
engine = WorkflowEngine(repository.load(workflow_id))
state = engine.state
guide = engine.recommendations()

engine.decide("scope_defined", True, rationale="Owner confirmed assets")
engine.inject_finding(title="Unexpected exposure", severity=7, confidence=60)
engine.enrich_finding(finding_id, evidence=["scanner://result/123"])
engine.update_finding_status(finding_id, FindingStatus.VALIDATED)
engine.resolve_action(action_id, note="Impact review completed")
engine.complete_step(override=False)
repository.save(workflow_id, engine.state)
```

The same boundary supports interactive and automated modes. A UI renders `Step`, `recommendations()`, open findings, and `progress_percent`; an agent consumes the same structured records and submits the same commands.

## Extension points

- Pass a custom ordered `Iterable[Step]` to `WorkflowEngine` for product-specific phases.
- Wrap `WorkflowEngine` in a repository that stores snapshots and/or forwards `audit_log` events to an append-only audit sink.
- Add policy-specific gates in `blockers()` or subclass the engine for regulated workflows.
- Use `mode="automated"` and the same command/recommendation protocol for agent orchestration; user-injected findings remain indistinguishable as durable domain objects except for `source`.
- Add an API adapter that accepts commands (`add_finding`, `decide`, `complete_step`, `resolve_action`) and returns state plus recommendations.

The engine is intentionally conservative: unknown IDs, corrupt state, invalid ranges, invalid lifecycle transitions, out-of-order completion, and unresolved closure work fail explicitly and leave the prior state intact.

## Completeness and edge-case guarantees

- Empty discovery is a valid branch: validation, impact, and remediation-only phases are recorded as skipped, then the workflow continues to reporting, closure, and archival.
- Open findings create validation actions; validated findings create impact actions; material findings create remediation actions; mitigated findings create verification actions. Obsolete actions are marked done, not deleted.
- Closure is unavailable while required actions or non-closed findings remain. No-finding closure is allowed after reporting.
- User or agent injection remains subject to identity, range, reference, and lifecycle validation. Out-of-order work requires an explicit, non-empty override rationale.
- Atomic snapshot writes and strict load validation make interruption and resume safe; audit records preserve what happened before and after a resume.
- Custom `Step` sequences are supported; a production adapter should validate that they contain a unique terminal `archive` step and that every step is reachable.
