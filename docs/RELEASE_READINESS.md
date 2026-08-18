# New-User Release Readiness Standard

This standard defines what "ready to release" means for a **brand-new user's
first day** with POCArchitect. It is deliberately **not a code-coverage
threshold**. Coverage measures which lines executed during tests; it says
nothing about whether a first-time user can install the tool, understand a
failure, exercise a feature, recover from a mistake, or find documentation that
matches reality. This standard measures those outcomes directly.

A release is **blocked** unless every pillar below passes. Enforcement is
automated by [`scripts/release_readiness.py`](../scripts/release_readiness.py),
which black-box exercises the **installed** CLI a new user actually runs. **No
exceptions:** every command and every user-facing option is exercised or
explicitly waived with a stated reason — see
[Option coverage, enforced](#option-coverage-enforced). It is invoked two ways
in CI (see [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)):

- The **`package` job** builds one wheel and source distribution, validates the
  packaged documentation, and uploads those exact artifacts.
- The **`release-readiness` matrix** installs those artifacts into disposable
  virtual environments on Linux, Windows, and macOS, then runs the gate against
  each install — proving what users receive, not what the working tree contains.
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
- During clean-artifact checks, the generated `pocarchitect` console executable
  itself runs `--version` and `--help` (not only `python -m pocarchitect`), and
  its entry point is registered. Source-tree runs use the module entry point.
- `pocarchitect --show-completion` emits a shell-completion script (the feature
  ships without requiring the user to first mutate their shell profile).

**CI gate:** the `release-readiness` matrix installs the built wheel on Linux
(minimum and maximum supported Python), Windows, and macOS, and installs the
source distribution on Linux. Each case uses a fresh `venv`, runs `pip check`,
and starts outside the checkout so editable source files and runner packages
cannot mask a packaging defect.

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
- The interactive `setup` wizard, run non-interactively, refuses with a clear
  exit code `2` and points the user at the scriptable alternative
  (`preflight` plus the provider key variable) instead of hanging on a prompt.
- The [Novice Usability Guide](NOVICE_USABILITY_GUIDE.md) ships a
  troubleshooting matrix and a "diagnose and fix" section.

---

## Pillar 3 — Full feature validation

**Standard:** Every user-facing command **and every option** behaves as
documented — validated by running it, not by inferring from line coverage.

Enforced checks:

- All required commands exist: `preflight`, `setup`, `config`, `batch-status`,
  `batch-reset`.
- **Option coverage is enforced** (see below): every `--long` option the CLI
  exposes is functionally exercised here or explicitly waived.
- `config` reports effective settings as machine-readable data **and never
  prints a secret in full** (keys are masked to a short prefix).
- `--dry-run` prints a compact summary and accepts `owner/repo` shorthand;
  `--dry-run --full` prints the entire prompt.
- The JSON dry-run is a stable two-event stream (`processing`, `dry_run`) and
  shorthand is expanded to a full GitHub URL in the emitted events.
- `--risk-level`, `--target-os`, and `--include-mitigations`/`--no-mitigations`
  are each reflected in the operator-preferences block of the assembled prompt.
- `--verbose` reports which model was selected.
- **A hermetic, real provider call** (see
  [Hermetic provider run](#hermetic-provider-run-the-old-boundary-closed))
  proves the options that only take effect on a live call:
  `--provider local` + `--base-url` route to the endpoint, `--model` and
  `--temperature` arrive on the wire unchanged, `--output-dir` receives the
  saved report with faithful metadata, and `--open` drives the viewer path.

Because the gate reads the command surface from the CLI's own metadata, a new
command that ships without validation and documentation trips Pillars 3 and 5.

### Option coverage, enforced

The gate enumerates every `--long` option from the live Typer command surface
(root callback and every subcommand) and requires each one to be either
**covered** — functionally exercised by a check above — or **waived** with a
recorded reason. The only current waiver is `--install-completion`, because it
writes to the user's shell profile (a side effect the gate must not cause); its
read-only sibling `--show-completion` is exercised in Pillar 1 instead. If a new
option ships without landing in the covered or waived set, this check fails —
that is the mechanism behind the "all options, no exceptions" guarantee.

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

## Hermetic provider run: the old boundary, closed

Earlier revisions of this standard stopped at the provider boundary and left a
live end-to-end run as a manual release step. That gap is now closed
**hermetically**: the gate starts an in-process, OpenAI-compatible **mock
server** on an ephemeral localhost port and drives a full `--provider local`
run against it — `preflight` reachability probe, prompt assembly, the
`POST /chat/completions` call, report save, and `--open`. The mock records the
request body, so the gate asserts that `--model` and `--temperature` reached the
wire unchanged, and reads the saved file to confirm `--output-dir` and metadata.
No network access and no credentials are involved.

The **only** first-day journey still not automated is a call to a **real, paid
provider** over the network. That needs a live credential that cannot be
exercised hermetically in CI, so a single real-provider smoke test remains a
**manual release step**, recorded in the release checklist. Everything up to and
including the provider request/response contract is now automated.

> Note: `--open` invokes the OS file viewer. On the Linux CI runner this is a
> headless no-op that still exercises the code path; the gate skips the actual
> launch on Windows to avoid opening a GUI application during a local run, and
> relies on the CI (Linux) run as the enforcement point for that option.

## Running the standard locally

```bash
python scripts/release_readiness.py            # human-readable report
python scripts/release_readiness.py --format json
```

For a true first-day simulation, build the artifacts and use the same
cross-platform clean-install driver as CI:

```bash
python -m build
python scripts/validate_fresh_install.py dist --artifact wheel
python scripts/validate_fresh_install.py dist --artifact sdist
```

Exit code `0` means release-ready; `1` means at least one pillar failed, and the
report names the exact check.
