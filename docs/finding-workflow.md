# Finding-driven guided workflow

`pocarchitect.finding_workflow` is a UI-agnostic workflow kernel. A client renders the current step, `blockers()`, and `recommendations()`, then sends commands back to the engine. The same commands work for a person, an automation, or an agent.

## Architecture and model

`WorkflowState` is the complete resumable snapshot: current phase and step, completed steps, findings, pending actions, decisions, audit log, derived risk, progress, mode, metadata, and terminal state. It contains no callbacks, so it can be serialized to JSON and stored behind a repository, API, or event-sourced projection.

`Finding` is a first-class object with identity, description, evidence, source, confidence, severity, tags, correlations, recommended actions, lifecycle history, and the status lifecycle:

```text
open -> validated -> exploited -> mitigated -> closed
                    \-> mitigated
```

Invalid status transitions are rejected. External observations are injected with `add_finding`; `enrich_finding` and `correlate` preserve the finding identity while improving context.

## Engine behavior

The default route is:

```text
scope -> authorize -> discover -> validate -> assess-impact
 -> plan-remediation -> verify-remediation -> report -> close -> archive
```

The route is linear by default, but findings create dynamic gates and actions. Open findings block impact, remediation, verification, and reporting until validated. Material validated/exploited findings (severity >= 4) produce a required remediation action. Closure requires every required action to be done and every finding to be closed. A documented `override=True` is available for emergency, legal, or policy exceptions and is always recorded in the audit log.

Risk is a transparent derived score: `sum(severity * confidence / 100)`. Clients can replace this with a policy adapter while keeping the state contract. `query_findings` supports status, severity, and tag filters.

## Guided client loop

1. Create `WorkflowEngine()` and render the current `Step` explanation and progress percentage.
2. Render `recommendations()`. Show blockers as mandatory, finding actions as contextual, and the current step as the primary call to action.
3. Record user decisions with `decide(key, value, rationale=...)`; decision gates currently include authorization and scope confirmation.
4. Convert every observation or agent result to a `Finding`, then enrich, correlate, validate, exploit-test, mitigate, and close it through the lifecycle API.
5. Complete the current step. On a blocked step, show `WorkflowError` and the exact `blockers()` text; there is no silent dead end.
6. Persist after each mutation using `save(path)` and resume with `WorkflowEngine.load(path)`. The atomic replace prevents partial snapshots after interruption.

## Extension points

- Pass a custom ordered `Iterable[Step]` to `WorkflowEngine` for product-specific phases.
- Wrap `WorkflowEngine` in a repository that stores snapshots and/or forwards `audit_log` events to an append-only audit sink.
- Add policy-specific gates in `blockers()` or subclass the engine for regulated workflows.
- Use `mode="automated"` and the same command/recommendation protocol for agent orchestration; user-injected findings remain indistinguishable as durable domain objects except for `source`.
- Add an API adapter that accepts commands (`add_finding`, `decide`, `complete_step`, `resolve_action`) and returns state plus recommendations.

The engine is intentionally conservative: unknown IDs, corrupt state, invalid ranges, invalid lifecycle transitions, out-of-order completion, and unresolved closure work fail explicitly and leave the prior state intact.
