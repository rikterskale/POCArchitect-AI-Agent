# POCArchitect Usage Guide

This document outlines all available command-line options for **POCArchitect**.

## Basic Usage

```bash
pocarchitect --url <POC_URL> --api-key <YOUR_API_KEY>
```

## Full Command Syntax

```bash
pocarchitect [OPTIONS]
```

## Options

### Required Options

| Option | Short | Description | Example |
|--------|-------|-------------|---------|
| `--url` | `-u` | Single PoC URL or path to a batch file | `--url https://github.com/user/repo` |
| `--api-key` | `-k` | API key for the chosen provider | `--api-key xai-...` |

### Core Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--provider` | `-p` | `xai` | LLM provider (xai or openai) |
| `--model` | `-m` | `grok-4` | Model to use (e.g. grok-4, gpt-4o) |
| `--output-dir` | `-o` | `./reports` | Directory where reports will be saved |
| `--temperature` | `-t` | `0.0` | Temperature for LLM generation (0.0 recommended) |

### Operator Control Flags (New)

| Option | Default | Description |
|--------|---------|-------------|
| `--risk-level` | `auto` | Force risk level: Critical, High, Medium, Low, or auto |
| `--target-os` | `auto` | Target OS: Windows, Linux, macOS, cross-platform, or auto |
| `--include-mitigations` | `True` | Include mitigation recommendations section |
| `--no-mitigations` | `False` | Disable mitigation recommendations |
| `--target-version` | `None` | Specific vulnerable version (e.g. 1.2.3) |

### Utility Flags

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--verbose` | `-v` | `False` | Enable verbose output (shows more details during processing) |
| `--dry-run` | | `False` | Show the final prompt without calling the LLM (great for testing) |
| `--version` | | `False` | Show version and exit |

## Examples

### 1. Basic Single URL

```bash
pocarchitect --url https://github.com/user/exploit-repo
```

### 2. With Operator Controls

```bash
pocarchitect --url https://github.com/example/poc-repo \
  --api-key xai-your_key_here \
  --risk-level Critical \
  --target-os Windows \
  --target-version 1.2.3
```

### 3. Disable Mitigations

```bash
pocarchitect --url https://github.com/example/poc-repo \
  --api-key xai-your_key_here \
  --no-mitigations
```

### 4. Dry Run (Recommended for testing)

```bash
pocarchitect --url https://github.com/example/poc-repo \
  --api-key xai-your_key_here \
  --dry-run
```

### 5. Batch Processing

```bash
pocarchitect --url example_usage/batch_urls.txt
```

### 6. Verbose + Custom Output Directory

```bash
pocarchitect --url https://github.com/example/poc-repo \
  --api-key xai-your_key_here \
  --output-dir ./my_reports \
  --verbose
```

## Batch File Format

Create a `batch_urls.txt` file with one URL per line:

```
https://github.com/user/exploit1
https://github.com/user/exploit2
https://raw.githubusercontent.com/user/raw-poc.py
```

## Environment Variables

You can also set the API key using environment variables:

- `XAI_API_KEY`
- `OPENAI_API_KEY`

### Example

```bash
export XAI_API_KEY=xai-your_key_here
pocarchitect --url https://github.com/example/poc-repo
```

## Dry-Run Mode

Use `--dry-run` to inspect the exact prompt that will be sent to the LLM without making any API call. This is very useful for:

- Debugging prompt quality
- Tuning operator flags
- Verifying zero-hallucination behavior

## Full Options
- pocarchitect --help

## Tips

- Always use `--dry-run` first when trying new flags or URLs.
- Set temperature to 0.0 for maximum consistency.
- Use `--verbose` when troubleshooting.
- Mount a volume when running in Docker to persist reports.

---

Last Updated: April 02, 2026

**For more details, see:**
- ARCHITECTURE.md
- DOCKER.md
