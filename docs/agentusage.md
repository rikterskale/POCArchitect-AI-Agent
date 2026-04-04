# POCArchitect Usage Guide

This document outlines all available command-line options for POCArchitect.

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--url` / `-u` | Single PoC GitHub URL | Required (or use `--batch`) |
| `--batch` / `-b` | Path to `.txt` file with multiple URLs (one per line) | None |
| `--provider` / `-p` | LLM provider: `xai`, `openai`, `groq`, `local` | `xai` |
| `--model` / `-m` | Model name | Provider-specific (e.g., `grok-3` for xai, `gpt-4o` for openai) |
| `--risk-level` | `Critical`, `High`, `Medium`, `Low` | `High` |
| `--target-os` | `Windows`, `Linux`, `macOS`, `cross-platform` | `Linux` |
| `--include-mitigations` / `--no-include-mitigations` | Include mitigation section | `true` |
| `--no-ingest` | Skip GitHub grounding | `false` |
| `--output-dir` | Output directory | `./reports` |
| `--verbose` / `-v` | Verbose output | `false` |
| `--dry-run` | Show full prompt without calling LLM | `false` |
| `--version` / `-V` | Show version and exit | — |

## Single URL Mode

```bash
pocarchitect --url https://github.com/example/poc-repo --provider xai
```

## Batch Mode

Pass a text file of URLs (one per line) using `--batch`:

```bash
pocarchitect --batch example_usage/batch_urls.txt --provider xai
```

The tool will process every URL in the file and generate one report per URL.

## Examples

Single PoC with custom settings:

```bash
pocarchitect --url https://github.com/... \
  --risk-level Critical \
  --target-os Windows \
  --no-include-mitigations
```

Batch processing:

```bash
pocarchitect --batch batch_urls.txt --provider openai --model gpt-4o
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

- Set temperature to 0.0 for maximum consistency.
- Use `--verbose` when troubleshooting.
- When switching providers, the model default adjusts automatically. Override with `--model` if needed.

**Last Updated:** April 03, 2026

For more details, see:

- `docs/architecture.md`
- `docs/docker-guide.md`
