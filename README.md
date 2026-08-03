# POCArchitect AI Agent

Turn any Proof-of-Concept URL (primarily GitHub repos, but can be others) into a clean, reproducible, **weaponized** Markdown blueprint for red teamers and offensive security operators.

## Features

- Shallow git clone + smart file extraction (grounding)
- Batch mode (`--batch batch_urls.txt`) — process multiple URLs from a text file
- Operator controls: `--risk-level`, `--target-os`, `--include-mitigations`, `--no-ingest`
- Automatic preflight checks on every run
- Multi-provider support: xAI/Grok (recommended), OpenAI, Groq, local Ollama
- Smart Docker support (reports saved to mounted `/reports` volume)
- Retry logic + timeouts on LLM calls
- `--dry-run` and `--verbose` flags

## Quick Start

New to terminals or Python? Start with the [Windows novice guide](docs/guides/WINDOWS_NOVICE_USABILITY_GUIDE.md) or [Linux novice guide](docs/guides/LINUX_NOVICE_USABILITY_GUIDE.md).

1. Clone the repo:

   ```
   git clone https://github.com/rikterskale/POCArchitect-AI-Agent.git
   cd POCArchitect-AI-Agent
   ```

2. Set up your API key:

   ```
   cp .env.example .env
   ```

   Edit `.env` and add your `XAI_API_KEY` (or `OPENAI_API_KEY` / `GROQ_API_KEY`).

3. Install:

   ```bash
   pip install -e .[all]
   ```

4. Verify:

   ```bash
   pocarchitect preflight --offline
   ```

   This verifies the installation without requiring a provider key. A real run performs the stricter provider-key check automatically.

5. Run a single PoC:

   ```bash
   pocarchitect --url https://github.com/example/poc-repo --provider xai
   ```

Reports are saved in `./reports/` (or `/reports` inside Docker).

Every generated report begins with a metadata block containing the source URL, provider, model, prompt asset, ingestion mode, timestamp, and a SHA-256 hash of the report body.

## Supported-platform matrix

| Platform/path | Status | Notes |
|---|---|---|
| Linux Bash | Supported in CI | CI exercises Ubuntu with Python 3.9–3.13. |
| Windows PowerShell | Supported by code; validate locally | Use `python -m pocarchitect`; native Windows CI is not configured. |
| WSL/Git Bash | Not separately validated | Treat as an alternative shell, not proof of native Windows support. |
| Docker Desktop/Linux Docker | Supported by Dockerfile; validate locally | Mount a writable host directory to `/reports`. |

## Batch progress and recovery

Batch runs write a resumable JSON ledger to `reports/batch_progress.json` by default. Pass `--batch-state path\to\state.json` to choose another location. Completed URLs are skipped on the next run; failed URLs remain eligible for retry.

## Command-Line Options

| Option | Description | Default |
|---|---|---|
| `--url`, `-u` | Single PoC GitHub URL | Required (or use `--batch`) |
| `--batch`, `-b` | Path to `.txt` file with multiple URLs | None |
| `--provider`, `-p` | LLM provider | `xai` |
| `--model`, `-m` | Model name | Provider-specific (e.g., `grok-3`) |
| `--risk-level` | Risk level | `High` |
| `--target-os` | Target OS | `Linux` |
| `--include-mitigations` | Include mitigations section | `true` |
| `--no-ingest` | Skip GitHub grounding | `false` |
| `--dry-run` | Show full prompt and exit (no API call) | `false` |
| `--verbose`, `-v` | Extra grounding details | `false` |
| `--version`, `-V` | Show version and exit | — |

Full help:

```bash
pocarchitect --help
```

The canonical CLI and configuration references are generated with:

```bash
python scripts/generate_docs.py
```

## Docker Usage

See `docs/docker-guide.md` for full instructions.

## Local Ollama Setup

See `docs/ollama-setup-guide.md`.
