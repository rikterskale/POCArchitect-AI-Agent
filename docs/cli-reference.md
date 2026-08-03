# CLI Reference

Generated from Typer command metadata by `python scripts/generate_docs.py`. CI fails when this runtime reference is stale.

## Main command

```text
Usage: python -m pocarchitect [OPTIONS] COMMAND [ARGS]...

 POCArchitect AI Agent - Turn messy PoCs into clean, reproducible blueprints.

+- Options -------------------------------------------------------------------+
| --url                  -u      TEXT                   Single PoC GitHub URL |
| --batch                -b      PATH                   Path to .txt file     |
|                                                       with multiple URLs    |
| --provider             -p      [xai|openai|groq|loca  [default: xai]        |
|                                l]                                           |
| --model                -m      TEXT                   Model name (default:  |
|                                                       provider-specific)    |
| --temperature          -t      FLOAT                  [default: 0.2]        |
| --base-url                     TEXT                                         |
| --output-dir                   PATH                                         |
| --risk-level                   TEXT                   [default: High]       |
| --target-os                    TEXT                   [default: Linux]      |
| --include-mitigations                                 [default: True]       |
| --no-ingest                                                                 |
| --dry-run                                             Show full prompt and  |
|                                                       exit without calling  |
|                                                       LLM                   |
| --verbose              -v                             Enable verbose output |
|                                                       (extra details during |
|                                                       grounding)            |
| --batch-state                  PATH                   JSON progress file    |
|                                                       used to resume        |
|                                                       completed batch URLs. |
| --yes                                                 Confirm source        |
|                                                       transfer without an   |
|                                                       interactive prompt.   |
| --format                       [text|json]            Output mode: text or  |
|                                                       JSON Lines.           |
|                                                       [default: text]       |
| --no-color                                            Disable ANSI color    |
|                                                       and style sequences.  |
| --version              -V                             Show version and exit |
| --help                                                Show this message and |
|                                                       exit.                 |
+-----------------------------------------------------------------------------+
+- Commands ------------------------------------------------------------------+
| preflight     Run environment preflight checks                              |
| batch-status  Show a concise, machine-readable summary of batch recovery    |
|               state.                                                        |
| batch-reset   Reset a ledger by moving its prior contents to a timestamped  |
|               backup.                                                       |
+-----------------------------------------------------------------------------+
```

## Provider preflight

```text
Usage: python -m pocarchitect preflight [OPTIONS]

 Run environment preflight checks

+- Options -------------------------------------------------------------------+
| --offline                                    Check installation without     |
|                                              requiring an API key or        |
|                                              provider access.               |
| --provider  -p      [xai|openai|groq|local]  Provider whose readiness to    |
|                                              check.                         |
|                                              [default: xai]                 |
| --base-url          TEXT                     OpenAI-compatible local        |
|                                              provider endpoint.             |
| --format            [text|json]              Output mode: text or JSON      |
|                                              Lines.                         |
|                                              [default: text]                |
| --no-color                                   Disable ANSI color and style   |
|                                              sequences.                     |
| --help                                       Show this message and exit.    |
+-----------------------------------------------------------------------------+
```

## Batch recovery status

```text
Usage: python -m pocarchitect batch-status [OPTIONS]

 Show a concise, machine-readable summary of batch recovery state.

+- Options -------------------------------------------------------------------+
| --batch-state        PATH  Batch ledger to inspect.                         |
|                            [default: reports\batch_progress.json]           |
| --help                     Show this message and exit.                      |
+-----------------------------------------------------------------------------+
```

## Batch recovery reset

```text
Usage: python -m pocarchitect batch-reset [OPTIONS]

 Reset a ledger by moving its prior contents to a timestamped backup.

+- Options -------------------------------------------------------------------+
| --batch-state        PATH  Batch ledger to reset.                           |
|                            [default: reports\batch_progress.json]           |
| --yes                      Confirm the recoverable reset without an         |
|                            interactive prompt.                              |
| --help                     Show this message and exit.                      |
+-----------------------------------------------------------------------------+
```

## Safe examples

```text
python -m pocarchitect preflight --provider local --offline
python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --no-color
python -m pocarchitect batch-status --batch-state reports/batch_progress.json
```
