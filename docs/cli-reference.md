# CLI Reference

Generated directly from Typer/Click command metadata by `python scripts/generate_docs.py`; it does not depend on terminal layout or platform path separators.

## Main command

POCArchitect AI Agent - Turn messy PoCs into clean, reproducible blueprints.

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--url`, `-u` | TEXT | None | Single PoC URL; public GitHub repositories can be grounded. |
| `--batch`, `-b` | PATH | None | Text file; blank lines and full-line # comments are ignored. |
| `--provider`, `-p` | xai \| openai \| groq \| local | xai | LLM provider to use. |
| `--model`, `-m` | TEXT | None | Model name (default: provider-specific) |
| `--temperature`, `-t` | FLOAT | 0.2 | Provider sampling temperature. |
| `--base-url` | TEXT | None | OpenAI-compatible endpoint for --provider local. |
| `--output-dir` | PATH | None | Directory where successful reports are written. |
| `--risk-level` | TEXT | High | Free-text risk label sent to the provider. |
| `--target-os` | TEXT | Linux | Free-text target environment sent to the provider. |
| `--include-mitigations`, `--no-mitigations` | BOOLEAN | True | Include mitigation instructions in the report (use --no-mitigations to omit). |
| `--no-ingest` | BOOLEAN | False | Skip GitHub repository grounding. |
| `--dry-run` | BOOLEAN | False | Show the prompt summary and exit without calling LLM |
| `--full` | BOOLEAN | False | With --dry-run, print the entire prompt instead of a summary. |
| `--open` | BOOLEAN | False | Open each finished report in your default viewer. |
| `--verbose`, `-v` | BOOLEAN | False | Enable verbose output (extra details during grounding) |
| `--batch-state` | PATH | None | JSON progress file used to resume completed batch URLs. |
| `--yes` | BOOLEAN | False | Confirm source transfer without an interactive prompt. |
| `--format` | text \| json | text | Output mode: text or JSON Lines. |
| `--no-color` | BOOLEAN | False | Disable ANSI color and style sequences. |
| `--version`, `-V` | BOOLEAN | False | Show version and exit |
| `--install-completion` | BOOLEAN | None | Install completion for the current shell. |
| `--show-completion` | BOOLEAN | None | Show completion for the current shell, to copy it or customize the installation. |

## Command: `preflight`

Run environment preflight checks

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--offline` | BOOLEAN | False | Check installation without requiring an API key or provider access. |
| `--provider`, `-p` | xai \| openai \| groq \| local | xai | Provider whose readiness to check. |
| `--base-url` | TEXT | None | OpenAI-compatible local provider endpoint. |
| `--output-dir` | PATH | None | Directory whose report-write access should be checked. |
| `--format` | text \| json | text | Output mode: text or JSON Lines. |
| `--no-color` | BOOLEAN | False | Disable ANSI color and style sequences. |

## Command: `doctor`

Diagnose installation, Git, output, and selected-provider readiness.

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--provider`, `-p` | xai \| openai \| groq \| local | xai | Provider whose readiness to check. |
| `--base-url` | TEXT | None | OpenAI-compatible local provider endpoint. |
| `--output-dir` | PATH | None | Directory whose report-write access should be checked. |
| `--offline` | BOOLEAN | False | Skip credentials and endpoint checks; diagnose the local installation only. |

## Command: `demo`

Generate a local demo report without credentials, network, or provider cost.

| Option | Type | Default | Purpose |
|---|---|---|---|
| — | — | — | No options |

## Command: `batch-status`

Show a concise, machine-readable summary of batch recovery state.

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--batch-state` | PATH | reports/batch_progress.json | Batch ledger to inspect. |

## Command: `batch-reset`

Reset a ledger by moving its prior contents to a timestamped backup.

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--batch-state` | PATH | reports/batch_progress.json | Batch ledger to reset. |
| `--yes` | BOOLEAN | False | Confirm the recoverable reset without an interactive prompt. |

## Command: `workflow-init`

Create a new auditable finding-driven workflow state file.

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--state` | PATH | reports/workflow.json | — |

## Command: `workflow-status`

Show the current workflow read model and recommendations.

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--state` | PATH | reports/workflow.json | — |

## Command: `workflow-apply`

Apply one auditable workflow command and persist the resulting state.

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--command` | TEXT | required | WorkflowEngine command name. |
| `--payload` | TEXT | {} | JSON object passed to the command. |
| `--state` | PATH | reports/workflow.json | — |

## Command: `setup`

Interactive first-run wizard: choose a provider, store a key, verify readiness.

| Option | Type | Default | Purpose |
|---|---|---|---|
| — | — | — | No options |

## Command: `config`

Show effective settings and where each value comes from (keys masked).

| Option | Type | Default | Purpose |
|---|---|---|---|
| — | — | — | No options |

## Commands

| Command | Purpose |
|---|---|
| `preflight` | Run environment preflight checks |
| `doctor` | Diagnose installation, Git, output, and selected-provider readiness. |
| `demo` | Generate a local demo report without credentials, network, or provider cost. |
| `batch-status` | Show a concise, machine-readable summary of batch recovery state. |
| `batch-reset` | Reset a ledger by moving its prior contents to a timestamped backup. |
| `workflow-init` | Create a new auditable finding-driven workflow state file. |
| `workflow-status` | Show the current workflow read model and recommendations. |
| `workflow-apply` | Apply one auditable workflow command and persist the resulting state. |
| `setup` | Interactive first-run wizard: choose a provider, store a key, verify readiness. |
| `config` | Show effective settings and where each value comes from (keys masked). |

## Safe examples

```text
python -m pocarchitect preflight --provider local --offline
python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --no-color
python -m pocarchitect --format json --no-color batch-status --batch-state reports/batch_progress.json
```

Root options such as `--format` and `--no-color` must appear before a subcommand name. Main-command options such as `--url` remain on the main command.
