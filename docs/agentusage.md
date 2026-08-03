# POCArchitect Usage Guide

This is a short orientation page. The complete, generated option list is the [CLI Reference](cli-reference.md); begin an installation or first run with the [Novice Usability Guide](NOVICE_USABILITY_GUIDE.md).

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--url` / `-u` | Single PoC GitHub URL | Required (or use `--batch`) |
| `--batch` / `-b` | Path to `.txt` file with multiple URLs (one per line) | None |
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
| `--format` | Text or JSON Lines output for main runs and `preflight` | `text` |
| `--no-color` | Disable terminal styling | `false` |
| `--version` / `-V` | Show version and exit | — |

## Safe single-URL preview

```bash
python -m pocarchitect --url https://github.com/example/poc-repo --no-ingest --dry-run --no-color
```

## Batch Mode

Pass a text file of URLs (one per line) using `--batch`. A real batch runs provider calls and asks for confirmation for each source transfer in an interactive terminal; use `--yes` only after reviewing an authorized batch.

```bash
python -m pocarchitect --batch example_usage/batch_urls.txt --provider xai
```

The tool will process every URL in the file and generate one report per URL.

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
python -m pocarchitect batch-status --batch-state reports/batch_progress.json
```

## Dry-Run Mode

Use `--dry-run` to inspect the exact prompt that will be sent to the LLM without making any API call. This is very useful for:

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
