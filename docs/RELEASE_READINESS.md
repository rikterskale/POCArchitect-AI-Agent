# New-User Release Readiness Standard

This standard defines what "ready to release" means for a **brand-new user's
first day** with POCArchitect. It is deliberately **not a code-coverage
threshold**. Coverage measures which lines executed during tests; it says
nothing about whether a first-time user can install the tool, understand a
failure, exercise a feature, recover from a mistake, or find documentation that
matches reality. This standard measures those outcomes directly.

A release is **blocked** unless every pillar below passes. Enforcement is
automated by [`scripts/release_readiness.py`](../scripts/release_readiness.py),
which black-box exercises the **installed** CLI a new user actually runs. It is
invoked two ways in CI (see [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)):

- The **`release-readiness` job** builds the wheel, installs it into a clean
  virtual environment, and runs the gate against that install — proving what a
  user receives, not what the working tree contains.
- The **test suite** runs the same gate (`tests/test_release_readiness.py`) so
  regressions are caught on every push, and `build` depends on both.

The gate is offline and deterministic: it makes no network calls, needs no
provider credentials, and scrubs provider keys from the environment so results
do not depend on the runner's secrets.

---

## Pillar 1 — Proven installation

**Standard:** A user who installs the published artifact can run the tool
immediately, with no source checkout and no credentials.

Enforced checks:

- `pocarchitect --version` runs and reports a version.
- `pocarchitect --help` runs and prints usage.
- `pocarchitect preflight --offline --format json` reports **Preflight passed**
  in a clean install (Python, dependencies, entry point, prompt asset, writable
  output directory).
- The `pocarchitect` console script is registered as an entry point (not only
  `python -m pocarchitect`).

**CI proof:** the `release-readiness` job installs **from the built wheel** into
a fresh `venv`, so an editable/source checkout cannot mask a packaging defect
(missing package data, broken entry point, unshipped module).

---

## Pillar 2 — Guided troubleshooting

**Standard:** Every failure a new user can hit explains how to fix itself. No
dead ends, no raw stack traces for expected error conditions.

Enforced checks:

- A failing preflight surfaces at least one failure **and every failing row
  carries a non-empty remediation** (the exact command or setting to fix it).
- The common provider errors map to specific, category-aware guidance:
  credential (401), rate limit (429), and unknown-model errors each produce a
  distinct, actionable message.
- A malformed GitHub URL is rejected **early** with an `Invalid PoC URL`
  message and a clean exit code — not a deep clone failure or traceback.
- The [Novice Usability Guide](NOVICE_USABILITY_GUIDE.md) ships a
  troubleshooting matrix and a "diagnose and fix" section.

---

## Pillar 3 — Full feature validation

**Standard:** Every user-facing command and primary journey behaves as
documented — validated by running it, not by inferring from line coverage.

Enforced checks:

- All required commands exist: `preflight`, `setup`, `config`, `batch-status`,
  `batch-reset`.
- `config` reports effective settings as machine-readable data **and never
  prints a secret in full** (keys are masked to a short prefix).
- `--dry-run` prints a compact summary and accepts `owner/repo` shorthand;
  `--dry-run --full` prints the entire prompt.
- The JSON dry-run is a stable two-event stream (`processing`, `dry_run`) and
  shorthand is expanded to a full GitHub URL in the emitted events.
- `--no-mitigations` is reflected in the assembled prompt
  (`Include Mitigations: No`).

Because the gate reads the command surface from the CLI's own metadata, a new
command that ships without validation and documentation trips Pillars 3 and 5.

---

## Pillar 4 — Tested recovery paths

**Standard:** When something goes wrong mid-run, the user can recover without
losing work or hand-editing state.

Enforced checks:

- `batch-status` summarizes an existing ledger (totals for success/failed).
- A completed URL is **skipped on resume** so re-running a batch does not repeat
  finished work or re-spend on provider calls.
- A corrupt ledger fails safely (exit 2) and **names the recovery command**
  (`batch-reset`) rather than discarding history.
- `batch-reset` retains a **recoverable timestamped backup** instead of deleting
  the ledger.
- An absent ledger yields a friendly message, not a stack trace.

---

## Pillar 5 — Documentation

**Standard:** The documentation a new user relies on is present, current, and
consistent with the actual command surface.

Enforced checks:

- Generated references are current — `scripts/generate_docs.py --check` reports
  no drift.
- All local Markdown links resolve (`scripts/validate_documentation_links.py`).
- The novice guides pass their validator (`scripts/validate_novice_guides.py`).
- **Every command appears in the generated CLI reference.**
- The README documents the safe first-run command and the `setup` wizard.

---

## Acknowledged boundary: live provider runs

The gate does not make a real provider call. A live end-to-end run needs a paid
credential and a network provider, which cannot be exercised hermetically in CI.
The dry-run path proves prompt assembly, redaction, and confirmation up to the
provider boundary; a single live smoke test remains a **manual release step**,
recorded in the release checklist. This boundary is intentional and is the only
first-day journey not automated here.

## Running the standard locally

```bash
python scripts/release_readiness.py            # human-readable report
python scripts/release_readiness.py --format json
```

For a true first-day simulation, run it against a wheel install rather than an
editable checkout:

```bash
python -m build
python -m venv /tmp/fresh
/tmp/fresh/bin/pip install dist/*.whl
/tmp/fresh/bin/python scripts/release_readiness.py
```

Exit code `0` means release-ready; `1` means at least one pillar failed, and the
report names the exact check.
