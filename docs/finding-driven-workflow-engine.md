# Finding-driven workflow engine

`pocarchitect.finding_workflow.WorkflowEngine` is the domain engine for a guided workflow. It is UI-agnostic: a CLI, web client, connector, or agent can render `snapshot()` and submit the same commands.

## Architecture

The engine has four deliberately separate concerns:

1. **Durable domain state** — `WorkflowState` stores the current phase and step, completed and skipped steps, findings, actions, decisions, audit events, scores, mode, and terminal state.
2. **Finding lifecycle** — `Finding` stores the observation, evidence, confidence, severity, relationships, recommended actions, metadata, and status history. The normal lifecycle is `open → validated → exploited → mitigated → closed`; invalid jumps fail safely.
3. **Policy and orchestration** — `WorkflowEngine` recalculates risk, priority, derived actions, blockers, branch skips, and progress after every mutation.
4. **Read model and persistence** — `snapshot()` is the stable UI/agent read model, including finding/action detail, decisions, audit history, scores, and guidance; `save()`/`load()` use atomic JSON replacement so an interrupted write does not corrupt resumability.

## Finding and state contracts

```python
finding = engine.inject_finding(
    title="Exposed service", severity=8, confidence=75,
    evidence=["scanner-result-123"], tags=["network"],
)
engine.enrich_finding(finding.id, description="...", evidence=["..."], tags=["internet-facing"])
engine.update_finding_status(finding.id, FindingStatus.VALIDATED, reason="Reproduced")
```

`WorkflowState.open_findings` and `WorkflowState.open_actions` are derived query helpers. `snapshot()` includes those lists, current guidance, scores, and progress so a client never needs to reconstruct workflow rules locally.

For product integration, `apply(command, **payload)` is the single command
boundary. Supported commands are `add_finding`, `inject_finding`,
`enrich_finding`, `update_finding_status`, `correlate`, `decide`,
`resolve_action`, and `complete_step`. A UI or agent can call
`can_complete(step_id)` to render blockers before committing and
`next_recommendation()` to obtain the highest-value guided prompt. Unknown
commands and malformed payloads fail with `WorkflowCommandError` instead of
being silently ignored.

## Guided flow and branching

The default route is scope → authorization → discovery → validation → impact → remediation planning → remediation verification → reporting → closure → archive. Authorization and scope decisions are explicit boolean decisions and are recorded with rationale and audit events.

An empty discovery result safely skips finding-specific work but still visits reporting, closure, and archive. A finding automatically creates validation, impact, treatment, and verification actions as its status advances. A user or agent may inject a finding at any point; the next recalculation immediately adds its actions and updates guidance. Out-of-order completion is supported only with an explicit, audited override rationale. Historical overrides never rewind the active guided position.

## Transparent policy rules

Risk is `Σ(severity × confidence/100)` across all findings. Priority uses the same base and applies a 1.25 exploitability multiplier to exploited findings; closed findings do not contribute to priority. Required blockers are:

- authorization before discovery;
- validation of all open findings before impact, remediation, or reporting;
- impact actions before remediation planning;
- remediation actions before verification;
- no required actions and no non-closed findings before closure.

These rules are intentionally small and inspectable. A future product can replace score calculation or branch policy by subclassing/wrapping the engine while retaining the state and command contracts.

## Completeness and edge cases

- Empty findings use a safe report route rather than ending early.
- Duplicate finding IDs, unknown references, invalid status jumps, unknown actions, blank decisions, and invalid score ranges raise `WorkflowError` without partial domain mutation.
- Correlation validates every referenced finding and removes self-links.
- Derived actions are reconciled, marked done rather than deleted, and retained in the audit-friendly state.
- Repeated completion of archive is idempotent; once archived, further step mutations are rejected.
- Every mutation is auditable, and JSON save/load preserves decisions, findings, histories, actions, skipped branches, and scores.
- `validate_integrity()` gives persistence/migration jobs a non-mutating health
  check for unknown steps, mismatched IDs, and dangling finding/action links.
- Custom routes are allowed to omit optional finding phases without causing a
  late finding to point at a nonexistent step; the default route retains the
  full validation and treatment path.
- Snapshot collections are defensive copies, so UI or agent code cannot mutate
  the live workflow by modifying returned findings, actions, decisions, or
  audit records.

## Product integration

At the application boundary, keep one engine per workflow ID. Render `snapshot()` for the guided screen, map buttons/forms/agent tools to `decide`, `add_finding`/`inject_finding`, `enrich_finding`, `update_finding_status`, `resolve_action`, and `complete_step`, then persist after each successful command. Interactive mode should show blockers and consequences before asking for confirmation; automated mode can consume the same recommendations and provide an override rationale when policy allows it.

## Reliability contract

`apply()` is the mutation boundary for UI and agent integrations. It is
transactional: if a command has an invalid payload or violates a workflow
rule, the complete in-memory state is restored before the error is returned.
This prevents partially enriched findings or half-applied branch decisions.

`query_findings()` returns defensive copies, while `snapshot()` is the full
read model. A client can therefore sort, annotate, or cache query results
without mutating the live workflow. `save()` accepts either a `Path` or string,
rejects invalid references before writing, and atomically replaces the target
JSON file. These guarantees make the same engine safe behind an HTTP API,
background worker, CLI, or agent loop.

Custom ordered routes may omit optional finding phases. The engine only applies
validation gates when a validation step exists, so a product-specific route
cannot strand an open finding at reporting; the normal closure gate still
requires the finding to be treated or explicitly handled.
