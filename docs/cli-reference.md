# CLI Reference

Generated directly from Typer/Click command metadata by `python scripts/generate_docs.py`; it does not depend on terminal layout or platform path separators.

## Main command

POCArchitect AI Agent - Turn messy PoCs into clean, reproducible blueprints.

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--url`, `-u` | STR | None | Single PoC URL; public GitHub repositories can be grounded. |
| `--source` | STR | None | Generic source identifier (GitHub URL, package, image, or download URL). |
| `--path` | DIRECTORY | None | Analyze a local, unpushed source directory. |
| `--batch`, `-b` | PATH | None | Text file; blank lines and full-line # comments are ignored. |
| `--provider`, `-p` | xai \| openai \| groq \| local | None | LLM provider (project config is used when omitted). |
| `--model`, `-m` | STR | None | Model name (default: provider-specific) |
| `--temperature`, `-t` | FLOAT | None | Provider sampling temperature. |
| `--base-url` | STR | None | OpenAI-compatible endpoint for --provider local. |
| `--output-dir` | PATH | None | Directory where successful reports are written. |
| `--risk-level` | STR | None | Free-text risk label sent to the provider. |
| `--target-os` | STR | None | Free-text target environment sent to the provider. |
| `--include-mitigations`, `--no-mitigations` | BOOLEAN | None | Include mitigation instructions in the report (use --no-mitigations to omit). |
| `--no-ingest` | BOOLEAN | False | Skip GitHub repository grounding. |
| `--dry-run` | BOOLEAN | False | Show the prompt summary and exit without calling LLM |
| `--full` | BOOLEAN | False | With --dry-run, print the entire prompt instead of a summary. |
| `--open` | BOOLEAN | False | Open each finished report in your default viewer. |
| `--verbose`, `-v` | BOOLEAN | False | Enable verbose output (extra details during grounding) |
| `--batch-state` | PATH | None | JSON progress file used to resume completed batch URLs. |
| `--yes` | BOOLEAN | False | Confirm source transfer without an interactive prompt. |
| `--max-estimated-cost` | FLOAT RANGE | None | Abort before a cloud call when estimated input cost exceeds this USD limit. |
| `--curate` | BOOLEAN | False | Interactively include/exclude selected grounding files. |
| `--dashboard` | BOOLEAN | False | Show the three-pane Rich run dashboard. |
| `--diff` | BOOLEAN | False | Compare the new report with the latest report for this source. |
| `--scaffold` | BOOLEAN | False | Create a runnable project skeleton after analysis. |
| `--scaffold-output` | PATH | None | Destination for --scaffold. |
| `--report-format` | markdown \| html \| pdf \| json | None | Also export each report in this format. |
| `--vuln-scan` | BOOLEAN | False | Enrich exact dependency versions with OSV records. |
| `--format` | text \| json | text | Output mode: text or JSON Lines. |
| `--no-color` | BOOLEAN | False | Disable ANSI color and style sequences. |
| `--version`, `-V` | BOOLEAN | False | Show version and exit |
| `--install-completion` | BOOLEAN | None | Install completion for the current shell. |
| `--show-completion` | BOOLEAN | None | Show completion for the current shell, to copy it or customize the installation. |

## Command: `preflight`

Run environment preflight checks. Example: pocarchitect preflight --offline

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--offline` | BOOLEAN | False | Check installation without requiring an API key or provider access. |
| `--provider`, `-p` | xai \| openai \| groq \| local | xai | Provider whose readiness to check. |
| `--base-url` | STR | None | OpenAI-compatible local provider endpoint. |
| `--output-dir` | PATH | None | Directory whose report-write access should be checked. |
| `--format` | text \| json | text | Output mode: text or JSON Lines. |
| `--no-color` | BOOLEAN | False | Disable ANSI color and style sequences. |

## Command: `doctor`

Diagnose readiness and optionally guide repairs. Example: pocarchitect doctor --offline --fix

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--provider`, `-p` | xai \| openai \| groq \| local | xai | Provider whose readiness to check. |
| `--base-url` | STR | None | OpenAI-compatible local provider endpoint. |
| `--output-dir` | PATH | None | Directory whose report-write access should be checked. |
| `--offline` | BOOLEAN | False | Skip credentials and endpoint checks; diagnose the local installation only. |
| `--fix` | BOOLEAN | False | Offer safe repairs for writable output and missing provider credentials. |
| `--yes` | BOOLEAN | False | Apply safe non-secret repairs without confirmation. |

## Command: `demo`

Generate a local demo report without credentials, network, or provider cost. Example: pocarchitect demo

| Option | Type | Default | Purpose |
|---|---|---|---|
| — | — | — | No options |

## Command: `quickstart`

Run the credential-free doctor and demo journey in one command. Example: pocarchitect quickstart

| Option | Type | Default | Purpose |
|---|---|---|---|
| — | — | — | No options |

## Command: `batch-status`

Show a concise, machine-readable summary of batch recovery state. Example: pocarchitect batch-status --batch-state reports/batch_progress.json

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--batch-state` | PATH | reports/batch_progress.json | Batch ledger to inspect. |

## Command: `batch-reset`

Reset a ledger by moving its prior contents to a timestamped backup. Example: pocarchitect batch-reset --yes

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--batch-state` | PATH | reports/batch_progress.json | Batch ledger to reset. |
| `--yes` | BOOLEAN | False | Confirm the recoverable reset without an interactive prompt. |

## Command: `workflow-init`

Create a new auditable finding-driven workflow state file. Example: pocarchitect workflow-init --state reports/workflow.json

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--state` | PATH | reports/workflow.json | — |

## Command: `workflow-status`

Show the current workflow read model and recommendations. Example: pocarchitect workflow-status --state reports/workflow.json

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--state` | PATH | reports/workflow.json | — |

## Command: `workflow-apply`

Apply one auditable workflow command and persist the resulting state. Example: pocarchitect workflow-apply --command confirm_scope --payload '{}'

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--command` | STR | required | WorkflowEngine command name. |
| `--payload` | STR | {} | JSON object passed to the command. |
| `--state` | PATH | reports/workflow.json | — |

## Command: `setup`

Interactive first-run wizard: choose a provider, store a key, verify readiness. Example: pocarchitect setup

| Option | Type | Default | Purpose |
|---|---|---|---|
| — | — | — | No options |

## Command: `config`

Show effective settings and where each value comes from (keys masked). Example: pocarchitect config

| Option | Type | Default | Purpose |
|---|---|---|---|
| — | — | — | No options |

## Command: `models`

Show provider defaults and practical model alternatives. Example: pocarchitect models

| Option | Type | Default | Purpose |
|---|---|---|---|
| — | — | — | No options |

## Command: `init`

Create .pocarchitect.toml defaults for the current repository. Example: pocarchitect init

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--force` | BOOLEAN | False | Replace an existing project config. |

## Command: `explore`

Browse curated examples and optionally run the local demo. Example: pocarchitect explore --run

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--run` | BOOLEAN | False | Generate the credential-free demo report. |

## Command: `history`

Show saved report versions and risk-analysis history. Example: pocarchitect history --output-dir reports

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--output-dir` | PATH | None | — |

## Command: `diff`

Compare two generated reports. Example: pocarchitect diff reports/old.md reports/new.md

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--output` | PATH | None | — |

## Command: `export`

Export a Markdown report as HTML or structured JSON. Example: pocarchitect export reports/report.md --format html

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--format` | markdown \| html \| pdf \| json | html | — |

## Command: `scaffold`

Generate a safe project skeleton from a completed report. Example: pocarchitect scaffold --report reports/report.md --output blueprint

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--report` | FILE | required | — |
| `--output` | PATH | poc-blueprint | — |

## Command: `compare`

Compare candidate PoCs using bounded, provider-free source inspection. Example: pocarchitect compare ./candidate-a ./candidate-b

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--output` | PATH | None | Optional Markdown matrix path. |

## Command: `plugins`

List registered analyzer plugins. Example: pocarchitect plugins

| Option | Type | Default | Purpose |
|---|---|---|---|
| — | — | — | No options |

## Command: `vulnerabilities`

Cross-reference exact dependency versions with the OSV database. Example: pocarchitect vulnerabilities .

| Option | Type | Default | Purpose |
|---|---|---|---|
| — | — | — | No options |

## Command: `publish`

Publish a report with the authenticated GitHub CLI and return its URL. Example: pocarchitect publish reports/report.md

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--public` | BOOLEAN | False | Create a public rather than secret Gist. |

## Commands

| Command | Purpose |
|---|---|
| `preflight` | Run environment preflight checks. Example: pocarchitect preflight --offline |
| `doctor` | Diagnose readiness and optionally guide repairs. Example: pocarchitect doctor --offline --fix |
| `demo` | Generate a local demo report without credentials, network, or provider cost. Example: pocarchitect demo |
| `quickstart` | Run the credential-free doctor and demo journey in one command. Example: pocarchitect quickstart |
| `batch-status` | Show a concise, machine-readable summary of batch recovery state. Example: pocarchitect batch-status --batch-state reports/batch_progress.json |
| `batch-reset` | Reset a ledger by moving its prior contents to a timestamped backup. Example: pocarchitect batch-reset --yes |
| `workflow-init` | Create a new auditable finding-driven workflow state file. Example: pocarchitect workflow-init --state reports/workflow.json |
| `workflow-status` | Show the current workflow read model and recommendations. Example: pocarchitect workflow-status --state reports/workflow.json |
| `workflow-apply` | Apply one auditable workflow command and persist the resulting state. Example: pocarchitect workflow-apply --command confirm_scope --payload '{}' |
| `setup` | Interactive first-run wizard: choose a provider, store a key, verify readiness. Example: pocarchitect setup |
| `config` | Show effective settings and where each value comes from (keys masked). Example: pocarchitect config |
| `models` | Show provider defaults and practical model alternatives. Example: pocarchitect models |
| `init` | Create .pocarchitect.toml defaults for the current repository. Example: pocarchitect init |
| `explore` | Browse curated examples and optionally run the local demo. Example: pocarchitect explore --run |
| `history` | Show saved report versions and risk-analysis history. Example: pocarchitect history --output-dir reports |
| `diff` | Compare two generated reports. Example: pocarchitect diff reports/old.md reports/new.md |
| `export` | Export a Markdown report as HTML or structured JSON. Example: pocarchitect export reports/report.md --format html |
| `scaffold` | Generate a safe project skeleton from a completed report. Example: pocarchitect scaffold --report reports/report.md --output blueprint |
| `compare` | Compare candidate PoCs using bounded, provider-free source inspection. Example: pocarchitect compare ./candidate-a ./candidate-b |
| `plugins` | List registered analyzer plugins. Example: pocarchitect plugins |
| `vulnerabilities` | Cross-reference exact dependency versions with the OSV database. Example: pocarchitect vulnerabilities . |
| `publish` | Publish a report with the authenticated GitHub CLI and return its URL. Example: pocarchitect publish reports/report.md |

## Safe examples

```text
python -m pocarchitect preflight --provider local --offline
python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --no-color
python -m pocarchitect --format json --no-color batch-status --batch-state reports/batch_progress.json
```

Root options such as `--format` and `--no-color` must appear before a subcommand name. Main-command options such as `--url` remain on the main command.
