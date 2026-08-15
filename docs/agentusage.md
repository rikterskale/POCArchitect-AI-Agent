# POCArchitect Usage Guide

This is a short orientation page. The complete, generated option list is the [CLI Reference](cli-reference.md); begin an installation or first run with the [Novice Usability Guide](NOVICE_USABILITY_GUIDE.md).

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--url` / `-u` | Single PoC GitHub URL | Required (or use `--batch`) |
| `--batch` / `-b` | Text input: blank lines and full-line `#` comments ignored | None |
| `--provider` / `-p` | LLM provider: `xai`, `openai`, `groq`, `local` | `xai` |
| `--model` / `-m` | Model name | Provider-specific (e.g., `grok-3` for xai, `gpt-4o` for openai) |
| `--temperature` / `-t` | Provider temperature | `0.2` |
| `--risk-level` | Free-text label sent to the provider | `High` |
| `--target-os` | Free-text label sent to the provider | `Linux` |
| `--include-mitigations` | Enables mitigation instructions; there is currently no public CLI switch to disable it | `true` |
| `--no-ingest` | Skip GitHub grounding | `false` |
| `--output-dir` | Output directory | `./reports` |
| `--verbose` / `-v` | Verbose output | `false` |
| `--dry-run` | Show full prompt without calling LLM | `false` |
| `--batch-state` | Custom JSON batch recovery ledger | `reports/batch_progress.json` during batch runs |
| `--yes` | Approve source transfer for noninteractive jobs | `false` |
| `--format` | Text or JSON Lines output; place before subcommands | `text` |
| `--no-color` | Disable terminal styling | `false` |
| `--version` / `-V` | Show version and exit | — |

## Safe single-URL preview

```bash
python -m pocarchitect --url https://github.com/example/poc-repo --no-ingest --dry-run --no-color
```

## Batch Mode

Pass a text file using `--batch`. Every nonblank line whose trimmed content does
not begin with `#` is an item; inline comments are not removed. A real batch
runs provider calls and asks for confirmation for each source transfer in an
interactive terminal; use `--yes` only after reviewing an authorized batch.

```bash
python -m pocarchitect --batch example_usage/batch_urls.txt --provider xai
```

The tool attempts every eligible URL. Dry run previews every non-resumed item.
Real item failures are persisted while later items continue; the command exits
1 after the summary if any item failed.

## Examples

Safe preview with custom settings:

```bash
python -m pocarchitect --url https://github.com/example/poc \
  --no-ingest \
  --dry-run \
  --risk-level Critical \
  --target-os Windows
```

Batch processing:

```bash
python -m pocarchitect --format json --no-color batch-status --batch-state reports/batch_progress.json
```

## Dry-Run Mode

Use `--dry-run` to inspect the exact prompt without making an LLM call. It
bypasses automatic preflight entirely, so use `preflight --offline` separately
when you also need installation/output checks. This is useful for:

- Debugging prompt quality
- Tuning operator flags
- Verifying zero-hallucination behavior

## Full Options

```bash
pocarchitect --help
```

## Tips

- `--temperature` is passed directly to the selected provider; supported ranges are provider-specific.
- Use `--verbose` when troubleshooting.
- When switching providers, the model default adjusts automatically. Override with `--model` if needed.

For provider credentials, output locations, and batch-state recovery, see [Configuration Reference](configuration-reference.md). For Docker and local-provider paths, see [Docker Guide](docker-guide.md) and [Local OpenAI-Compatible Provider Guide](ollama-setup-guide.md).
