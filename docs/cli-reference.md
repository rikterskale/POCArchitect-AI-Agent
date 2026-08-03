# CLI Reference

Generated directly from Typer/Click command metadata by `python scripts/generate_docs.py`; it does not depend on terminal layout or platform path separators.

## Main command

POCArchitect AI Agent - Turn messy PoCs into clean, reproducible blueprints.

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--url`, `-u` | TEXT | None | Single PoC GitHub URL |
| `--batch`, `-b` | PATH | None | Path to .txt file with multiple URLs |
| `--provider`, `-p` | xai | openai | groq | local | xai | — |
| `--model`, `-m` | TEXT | None | Model name (default: provider-specific) |
| `--temperature`, `-t` | FLOAT | 0.2 | — |
| `--base-url` | TEXT | None | — |
| `--output-dir` | PATH | None | — |
| `--risk-level` | TEXT | High | — |
| `--target-os` | TEXT | Linux | — |
| `--include-mitigations` | BOOLEAN | True | — |
| `--no-ingest` | BOOLEAN | False | — |
| `--dry-run` | BOOLEAN | False | Show full prompt and exit without calling LLM |
| `--verbose`, `-v` | BOOLEAN | False | Enable verbose output (extra details during grounding) |
| `--batch-state` | PATH | None | JSON progress file used to resume completed batch URLs. |
| `--yes` | BOOLEAN | False | Confirm source transfer without an interactive prompt. |
| `--format` | text | json | text | Output mode: text or JSON Lines. |
| `--no-color` | BOOLEAN | False | Disable ANSI color and style sequences. |
| `--version`, `-V` | BOOLEAN | False | Show version and exit |

## Command: `preflight`

Run environment preflight checks

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--offline` | BOOLEAN | False | Check installation without requiring an API key or provider access. |
| `--provider`, `-p` | xai | openai | groq | local | xai | Provider whose readiness to check. |
| `--base-url` | TEXT | None | OpenAI-compatible local provider endpoint. |
| `--format` | text | json | text | Output mode: text or JSON Lines. |
| `--no-color` | BOOLEAN | False | Disable ANSI color and style sequences. |

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

## Commands

| Command | Purpose |
|---|---|
| `preflight` | Run environment preflight checks |
| `batch-status` | Show a concise, machine-readable summary of batch recovery state. |
| `batch-reset` | Reset a ledger by moving its prior contents to a timestamped backup. |

## Safe examples

```text
python -m pocarchitect preflight --provider local --offline
python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --no-color
python -m pocarchitect batch-status --batch-state reports/batch_progress.json
```
