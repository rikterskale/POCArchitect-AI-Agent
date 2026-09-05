# POCArchitect AI Agent

> Turn authorized PoC source into tested, evidence-backed implementations.

POCArchitect is a command-line tool that reviews authorized Proof-of-Concept
(PoC) sources, produces structured analysis and candidate implementation
bundles, and proves reviewed implementations through an explicit build-and-test
contract. It accepts GitHub repositories, local directories, package/image
identifiers, and download URLs; GitHub and local sources can be used as bounded,
redacted grounding.

Analysis never executes retrieved code. Execution occurs only through the
separate, operator-confirmed `verify run` command in a network-isolated,
read-only, non-root Docker sandbox. A report or scaffold is a candidate—not a
working-PoC claim. POCArchitect emits VERIFIED only after every contracted build,
test, and artifact check passes and durable JSON evidence is written.

## Features

- Guided first-run `setup` wizard and a `config` command that shows effective settings (keys masked)
- Shallow GitHub clone and source-file selection for grounding
- `owner/repo` shorthand and early URL validation
- Batch mode (`--batch batch_urls.txt`) with a live progress bar and ETA
- Operator controls: `--risk-level`, `--target-os`, `--include-mitigations/--no-mitigations`, `--no-ingest`
- Provider-aware preflight checks with actionable fix hints; `--dry-run` bypasses automatic preflight entirely
- `doctor` installation/provider diagnosis and a credential-free `demo` report
- Ingestion preview with a rough cost estimate before any provider call
- Cloud providers (`xai`, `openai`, `groq`) and a local OpenAI-compatible endpoint (`local`)
- Docker image with a writable `/reports` volume
- Retry logic + timeouts on LLM calls; fast, friendly errors for unknown models
- Reports print their absolute path with an optional `--open`, plus a short preview
- Finding-driven workflow kernel with resumable guided state, lifecycle gates, and audited recommendations
- Auditable workflow CLI (`workflow-init`, `workflow-status`, `workflow-apply`) for durable finding handling
- Shell completion (`--install-completion`), `--dry-run` (summary, or `--full`), and `--verbose`
- Rich three-pane dashboard, per-phase timing, grounding curation, and a post-run summary card
- Dry-run sample report, inferred Mermaid architecture, report history/diffs, and HTML/PDF/JSON export
- Local-directory analysis, multi-source comparison, OSV vulnerability enrichment, and analyzer plugins
- Path-safe implementation-bundle materialization and draft verification contracts
- Evidence-backed working-PoC verification with locked-down Docker execution, explicit authorization, and fail-closed status
- Per-repository `.pocarchitect.toml`, example gallery, and typo suggestions
- Reusable GitHub Action, pre-commit hook, scheduled workflow template, and optional Gist publishing
- Production-focused local web GUI with a one-click credential-free demo,
  readable accessible navigation, smart provider selection and refresh, exact
  transfer re-estimation, resilient live progress, complete session report
  discovery, and launch-scoped security controls

## Feature status

| Capability | Status | Extra setup |
|---|---|---|
| Safe dry run, preflight, doctor, demo | Stable | None |
| Cloud providers (`xai`, `openai`, `groq`) | Stable | Provider key and network access |
| Local OpenAI-compatible provider | Stable integration boundary | Running endpoint and compatible model |
| GitHub grounding and batch recovery | Stable | Public authorized repositories; Git |
| Finding-driven workflow kernel | Stable library capability | Integrate through the documented workflow API |
| Local source, history/diff, export, scaffold, comparison | Stable | None |
| Working-PoC build/test verification | Stable | Running Docker and a reviewed local toolchain image |
| OSV enrichment and report publishing | Opt-in integration | Network; authenticated `gh` for publishing |
| ARM64/Apple Silicon/Windows ARM | Experimental/untested | Validate Git, Docker, and local-provider compatibility on the host |

## Start here

**New user? Begin with [Start Here: POCArchitect](docs/START_HERE.md).** It is
the novice-first path from installing Python, Git, and Docker through a safe
local demo, the first evidence-backed VERIFIED PoC, finding remediation,
troubleshooting, updates, and cleanup. Every major step includes an expected
result and recovery path.

The older [Novice Usability Guide](docs/NOVICE_USABILITY_GUIDE.md) remains the
validation-oriented CLI reference. The [Command Guide](docs/command-guide.md)
covers advanced and automated workflows.

After installation, the shortest credential-free proof is:

```bash
python -m pocarchitect quickstart
```

This runs the offline installation diagnosis and creates a local demo report.

## Install

PyPI is not a supported installation path for this project. Use a source
checkout or a project release artifact; both paths are validated by CI.

For a source checkout:

```bash
git clone https://github.com/rikterskale/POCArchitect-AI-Agent.git
cd POCArchitect-AI-Agent
python -m venv .venv
# Activate .venv, then:
python -m pip install -e ".[all]"
python -m pocarchitect doctor --offline
python -m pocarchitect demo
```

To add the optional local GUI:

```bash
python -m pip install -e ".[gui]"
pocarchitect gui
```

The GUI binds only to `127.0.0.1`, opens with a launch-specific session, and
keeps prepared source content in backend memory. A provider call begins only
after the transfer review is explicitly approved. Changing the selected files
recalculates transfer size, token, cost, and redaction metadata before approval.
Select **Create credential-free demo** on first launch to reach a complete local
report without entering a source, configuring a provider, or making a network
request.

For a release artifact, download the matching wheel or source distribution from
the project's release assets and install it in a fresh virtual environment:

```bash
python -m pip install dist/pocarchitect-0.3.0-py3-none-any.whl
python -m pocarchitect doctor --offline
python -m pocarchitect demo
```

After installing, the quickest guided path is the interactive wizard, which stores a provider key in a local `.env` and checks readiness:

```bash
pocarchitect setup
```

From the repository root, a safe first run is:

```bash
python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --no-color
```

This command does not clone the example repository, contact an LLM provider, create a report, or require a credential. It prints a compact summary. Add `--format json` for machine-readable events or `--full` to inspect the complete prompt.

For installation and an offline readiness check, follow the guide or run:

```bash
python -m pip install -e ".[all]"
python -m pocarchitect preflight --offline --format json --no-color
```

For a non-editable local install, use `python -m pip install .`. Release CI
builds a wheel and source distribution, but does not publish them to PyPI.

`preflight --offline` verifies Python, the five declared runtime imports, the
package entry point, the prompt asset, and the resolved writable output
directory. Grounded runs additionally require a runnable Git executable; use
`doctor` without `--offline` when you want to check that capability explicitly. A real
cloud-provider run additionally checks the matching provider key. Local
preflight requests only `<base-url>/models`; it does not test chat completions
or model suitability.

On Windows, help is rendered as plain text so diagnostic capture remains safe:

```powershell
python -m pocarchitect --help > help.txt
python -m pocarchitect --help | Select-Object -First 20
```

## Supported-platform matrix

| Platform/path | Status | Notes |
|---|---|---|
| Linux Bash | CI-gated | Unit tests cover Python 3.10–3.14; the first-run matrix installs wheels on 3.10/3.14 and the sdist on 3.12. |
| Windows PowerShell | CI-gated | The first-run matrix installs the wheel on Windows/Python 3.12 and runs the offline readiness gate. |
| macOS | CI-gated | The first-run matrix installs the wheel on macOS/Python 3.12 and runs the offline readiness gate. |
| WSL/Git Bash | Not separately validated | Treat as an alternative shell, not proof of native Windows support. |
| Linux Docker | Validated in CI | CI builds the image, checks help/report persistence, and runs a real candidate through the restricted verifier with retained evidence. Mount a writable host directory to `/reports` for reports. |
| Docker Desktop | Not separately validated | Native bind mounts, path conversion, TTY behavior, and provider-backed runs remain manual/best-effort. |
| ARM64/Apple Silicon/Windows ARM | Not separately validated | The package is pure Python, but provider, Git, Docker, and local-model compatibility depends on the host; use `doctor` and `demo` after installation. |

Python 3.10–3.14 are CI-supported. Native x86_64 Linux, Windows, and macOS are
the primary support targets. ARM64/Apple Silicon, WSL/Git Bash, and Docker
Desktop are best-effort host paths and are not release-blocking validation
targets today.

## Prove a PoC works

Generate or review a candidate implementation, then create its explicit
verification contract:

```bash
pocarchitect verify init ./authorized-poc \
  --authorization "customer-owned isolated lab"
```

Review the generated `.pocarchitect/poc-verification.json`, its commands, every
implementation file, and the acceptance tests. Review and pull the declared
Docker image yourself; the verifier never pulls images implicitly. When the
implementation is ready, set `implementation_status` to `ready` and run:

```bash
pocarchitect verify run ./authorized-poc --yes
```

The verifier copies a bounded, secret-filtered source snapshot into an ephemeral
container with no network, a read-only root filesystem, a non-root user, no
Linux capabilities, `no-new-privileges`, and CPU/memory/process/time limits. A
zero exit and `poc_verified` event are accompanied by private JSON evidence that
binds the source, contract, resolved image ID, sandbox controls, and every step
result. See the [Working PoC Verification Guide](docs/verification-guide.md) for
the contract schema, threat model, examples, and limitations.

## Batch progress and recovery

Batch runs write a version-2 resumable JSON ledger to
`reports/batch_progress.json` by default. Pass
`--batch-state path\to\state.json` to choose another location. Completed URLs
are skipped on the next run; failed URLs remain eligible for retry. The command
processes every eligible dry-run item and exits 1 after a completed batch if any
item failed, so automation can use both the exit code and the final
`batch_complete.failed` field. Inspect or reset a ledger with `batch-status` and
`batch-reset`; see the [CLI Reference](docs/cli-reference.md).

## Provider model defaults

| Provider | Default model |
|---|---|
| `xai` | `grok-4.6` |
| `openai` | `gpt-4o` |
| `groq` | `openai/gpt-oss-120b` |
| `local` | `qwen2.5-coder:14b` |

The CLI exposes exactly `xai`, `openai`, `groq`, and `local`. Claude/Gemini
wording in the packaged prompt describes prompt portability, not additional CLI
provider choices. Configure another OpenAI-compatible endpoint through
`--provider local --base-url <URL>`.

## Common command options

| Option | Description | Default |
|---|---|---|
| `--url`, `-u` | Single PoC GitHub URL (or `owner/repo` shorthand) | Required (or use `--batch`) |
| `--source` | GitHub URL, package/image identifier, or download URL | None |
| `--path` | Local source directory, including unpushed code | None |
| `--batch`, `-b` | Path to `.txt` file with multiple URLs | None |
| `--provider`, `-p` | LLM provider | `xai` |
| `--model`, `-m` | Model name | Provider-specific (e.g., `grok-4.6`) |
| `--temperature`, `-t` | Provider temperature | `0.2` |
| `--risk-level` | Free-text risk label sent to the provider | `High` |
| `--target-os` | Free-text target label sent to the provider | `Linux` |
| `--include-mitigations` / `--no-mitigations` | Include mitigation instructions; use `--no-mitigations` to omit | `true` |
| `--no-ingest` | Skip GitHub grounding | `false` |
| `--dry-run` | Show a prompt summary and exit (no API call); add `--full` for the entire prompt | `false` |
| `--full` | With `--dry-run`, print the entire prompt instead of a summary | `false` |
| `--open` | Open each finished report in the OS default viewer | `false` |
| `--verbose`, `-v` | Extra grounding details | `false` |
| `--batch-state` | Custom resumable batch-ledger path | `reports/batch_progress.json` for batch runs |
| `--max-estimated-cost` | Abort before a cloud call above this estimated USD input-cost limit | None |
| `--curate` | Interactively exclude selected grounding files before transfer | `false` |
| `--dashboard` | Render run progress, grounding files, and report preview in three panes | `false` |
| `--diff` | Save a unified diff against the latest report for the source | `false` |
| `--scaffold` | Materialize a candidate implementation and draft verification contract | `false` |
| `--report-format` | Also export as `html`, `pdf`, or `json` | Project config / `markdown` |
| `--vuln-scan` | Query OSV for exact dependency versions found in grounding | `false` |
| `--format` | Text or JSON Lines output for main runs and `preflight` | `text` |
| `--no-color` | Disable terminal styling | `false` |
| `--version`, `-V` | Show version and exit | — |

Full help:

```bash
pocarchitect --help
```

Useful no-cost diagnostics:

```bash
python -m pocarchitect --format json --no-color doctor --offline
python -m pocarchitect --format json --no-color demo
python -m pocarchitect models
python -m pocarchitect explore
python -m pocarchitect init
```

## Product workflow

Create reusable defaults and analyze an unpushed checkout:

```bash
pocarchitect init
pocarchitect --path . --curate --dashboard --vuln-scan --diff --scaffold --report-format html
```

Preview the complete report shape without provider spend, compare candidate repositories,
and inspect saved versions:

```bash
pocarchitect --source pypi:example-package --no-ingest --dry-run
pocarchitect compare ./candidate-a ./candidate-b --output reports/comparison.md
pocarchitect history
pocarchitect export reports/POCAnalysis_example.md --format pdf
```

`action.yml` provides a reusable GitHub Action and `.pre-commit-hooks.yaml` exposes a
credential-free local check. The scheduled workflow is safe by default and can be adapted
to an authenticated provider run when a team wants persisted trend reports.

For the browser interface, install the optional GUI dependencies and launch the
local workspace:

```bash
python -m pip install -e ".[gui]"
pocarchitect gui
```

Use `pocarchitect gui --no-open` when the environment cannot open a browser;
the command prints a one-time protected launch URL. The GUI is intentionally
local-only and does not provide a remotely bindable server mode.

The interface supports keyboard navigation, reduced-motion preferences,
responsive desktop/mobile layouts, interrupted-progress recovery, and a
searchable local report library. Active runs are recovered after a page refresh
for as long as the launch process remains running. It preselects an available
cloud provider, can detect a newly added provider key without a GUI restart, and
keeps reports from custom output directories discoverable for the current
session. CLI and GUI demo reports under `reports/demo/` also appear in the
library.

`doctor` checks the installation and selected provider readiness. `demo` uses a
deterministic offline response and writes a real Markdown report under
`reports/demo/`; it starts no server and requires no credentials, network, or
provider spend.

Version tags matching `v<project-version>` trigger the release workflow. It
builds and clean-installs both distributions, validates package contents,
generates SHA-256 checksums, records build provenance, and publishes the
verified files as GitHub release assets.

The CLI reference is generated from Typer/Click metadata. The configuration
reference imports provider maps and defaults from `pocarchitect/config.py`;
its explanatory policy text remains reviewed source in the generator. Regenerate
both with:

```bash
python scripts/generate_docs.py
```

## Documentation

- [Start Here: POCArchitect](docs/START_HERE.md) — novice-first installation,
  GUI, VERIFIED PoC, remediation, safety, and troubleshooting journey.
- [Novice Usability Guide](docs/NOVICE_USABILITY_GUIDE.md) — installation, safe first use, troubleshooting, cleanup, and update instructions.
- [Command Guide](docs/command-guide.md) — end-to-end Windows, macOS/Linux, provider, batch, automation, Docker, and development commands.
- [CLI Reference](docs/cli-reference.md) — generated option and subcommand reference.
- [Configuration Reference](docs/configuration-reference.md) — provider keys, defaults, precedence, and output settings.
- [Docker Guide](docs/docker-guide.md) — image build, safe runs, provider confirmation, and report mounts.
- [Working PoC Verification Guide](docs/verification-guide.md) — candidate materialization, build/test contracts, sandbox controls, evidence, and VERIFIED semantics.
- [Local OpenAI-Compatible Provider Guide](docs/ollama-setup-guide.md) — Ollama-specific setup notes and limitations.
- [Architecture](docs/architecture.md) — implementation-oriented component overview.
- [Finding-driven workflow engine](docs/finding-driven-workflow-engine.md) — architecture, lifecycle, branching, persistence, and product integration contract.
- [Finding-driven workflow quickstart](docs/finding-workflow.md#first-cli-workflow) — complete durable workflow example from initialization to archival.
- [Documentation Gap Analysis](docs/DOCUMENTATION_GAP_ANALYSIS.md) — current-tree evidence, all 28 findings, and verified remediation closure matrix.
- [Release Readiness Standard](docs/RELEASE_READINESS.md) — the six-pillar new-user readiness gate enforced in CI.
- [Validation Claims and Evidence Policy](docs/VALIDATION_CLAIMS.md) — distinguishes current repository claims, hosted CI results, manual external checks, and historical snapshots.
- [Documentation Review Report](docs/DOCUMENTATION_REVIEW_REPORT.md) — **historical snapshot** of commit `60d55d47c7ceb621df2f124764f01403a99f346b`; do not use it as current behavior or validation evidence.

## Safety and authorization

Only analyze repositories you are authorized to inspect. GitHub grounding clones a public repository into a temporary directory, then sends selected, redacted source content to the selected provider only after confirmation. `--yes` bypasses the confirmation prompt and is intended only for an already-reviewed, authorized noninteractive job. Provider calls may incur charges under the provider account.

## Update and support

To update a checkout, run `git pull`, reactivate the virtual environment, run `python -m pip install -e ".[all]"`, then rerun the offline preflight. Report problems with the command, operating system, Python version, provider name (never the key), and output from `python -m pocarchitect preflight --offline --format json --no-color` at the [issue tracker](https://github.com/rikterskale/POCArchitect-AI-Agent/issues).

## License

See [LICENSE](LICENSE).
