# POCArchitect AI Agent

Turn any Proof-of-Concept URL (primarily GitHub repos) into a clean, reproducible, **weaponized** Markdown blueprint for red teamers and offensive security operators.

## Features

- Shallow git clone + smart file extraction (grounding)
- Fully functional batch mode (`--url batch_urls.txt`)
- Operator controls: `--risk-level`, `--target-os`, `--include-mitigations`, `--no-ingest`
- Automatic preflight checks on every run
- Multi-provider support: xAI/Grok (recommended), OpenAI, Groq, local Ollama
- Smart Docker support (reports saved to mounted `/reports` volume)
- Retry logic + timeouts on LLM calls
- `--dry-run` and `--verbose` flags

## Quick Start

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
   pocarchitect preflight
   ```

5. Run a single PoC:

   ```bash
   pocarchitect --url https://github.com/example/poc-repo --provider xai
   ```

Reports are saved in `./reports/` (or `/reports` inside Docker).

## Command-Line Options

| Option | Description | Default |
|---|---|---|
| `--url`, `-u` | Single URL or path to batch `.txt` file | Required |
| `--provider`, `-p` | LLM provider | `xai` |
| `--model`, `-m` | Model name | `grok-3` |
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

## Docker Usage

See `docs/docker-guide.md` for full instructions.

## Local Ollama Setup

See `docs/ollama-setup-guide.md`.