# POCArchitect Command Guide

This end-to-end reference documents POCArchitect 0.2.0 commands. Run commands
from the repository root. Analyze only repositories you are authorized to
inspect. Never put credentials on a command line or commit a `.env` file.

## Quick choices

| Goal | Command |
|---|---|
| Show CLI help | `pocarchitect --help` |
| Verify installation, no credentials needed | `pocarchitect preflight --offline` |
| Safely inspect a prompt | `pocarchitect --url https://github.com/example/poc --no-ingest --dry-run` |
| Analyze one authorized URL | `pocarchitect --url <AUTHORIZED_GITHUB_URL> --provider <provider>` |
| Process a list with recovery state | `pocarchitect --batch batch_urls.txt --provider <provider>` |
| Inspect/reset a batch ledger | `pocarchitect batch-status` / `pocarchitect batch-reset` |

Replace angle-bracket placeholders with your own values.

## Installation

### Windows PowerShell

```powershell
git clone https://github.com/rikterskale/POCArchitect-AI-Agent.git
Set-Location POCArchitect-AI-Agent
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[all]"
```

If execution policy blocks activation, set it for the current shell only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Use another installed Python 3.10+ selector if `py -3.10` is unavailable.

### macOS and Linux (Bash/Zsh)

```bash
git clone https://github.com/rikterskale/POCArchitect-AI-Agent.git
cd POCArchitect-AI-Agent
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[all]"
```

### Update an existing checkout

Activate the virtual environment, then run:

```bash
git pull
python -m pip install -e ".[all]"
pocarchitect preflight --offline
```

Use `git pull --ff-only` if you do not want a merge commit.

## Installation and readiness checks

```bash
pocarchitect --version
pocarchitect --help
pocarchitect preflight --offline
```

Offline preflight checks Python, the installed package, prompt asset, and the
default output directory. It neither contacts a provider nor needs a key.

For JSON Lines output suitable for CI:

```bash
pocarchitect preflight --offline --format json --no-color
```

If the console command is unavailable, use the module form:

```bash
python -m pocarchitect --help
python -m pocarchitect preflight --offline
```

## Single-URL commands

### Safe first run

```bash
pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --format json --no-color
```

This does not clone a repository, call a provider, require credentials, or
create a report. It ends with a `dry_run` JSON event.

### Inspect authorized GitHub grounding without an LLM call

```bash
pocarchitect --url <AUTHORIZED_GITHUB_URL> --dry-run --verbose
```

Without `--no-ingest`, the URL can be shallow-cloned and selected content can
be present in the prompt preview. `--dry-run` prevents the provider call and
report creation, but does not disable that local grounding behavior.

### Interactive real run

```bash
pocarchitect --url <AUTHORIZED_GITHUB_URL> --provider openai
```

The tool previews the planned source transfer and asks for confirmation. A
Markdown report is written to `reports/` only after a successful provider call.
Choose another writable destination when needed:

```bash
pocarchitect --url <AUTHORIZED_GITHUB_URL> --provider openai --output-dir reports/client-a
```

### Change analysis context

```bash
pocarchitect --url <AUTHORIZED_GITHUB_URL> \
  --provider openai \
  --model <MODEL_NAME> \
  --temperature 0.2 \
  --risk-level Critical \
  --target-os Windows \
  --verbose
```

`--risk-level` and `--target-os` are free-text labels. Mitigation instructions
are enabled by default with `--include-mitigations`; there is presently no
public disable flag.

### Reviewed, noninteractive job

```bash
pocarchitect --url <AUTHORIZED_GITHUB_URL> --provider openai --yes --no-color
```

`--yes` bypasses transfer confirmation. Use it only after independently
reviewing and authorizing every target and transfer.

### Main-command option reference

| Option | Purpose | Default |
|---|---|---|
| `--url`, `-u` | One URL; required unless `--batch` is used. | None |
| `--batch`, `-b` | Text file with one URL per line. | None |
| `--provider`, `-p` | `xai`, `openai`, `groq`, or `local`. | `xai` |
| `--model`, `-m` | Provider model override. | Provider-specific |
| `--temperature`, `-t` | Provider sampling temperature. | `0.2` |
| `--base-url` | Local OpenAI-compatible endpoint. | `http://localhost:11434/v1` |
| `--output-dir` | Report destination. | `reports/` (`/reports` in Docker) |
| `--risk-level` | Free-text risk label. | `High` |
| `--target-os` | Free-text target label. | `Linux` |
| `--include-mitigations` | Enables mitigation instructions. | `true` |
| `--no-ingest` | Skip GitHub source grounding. | `false` |
| `--dry-run` | Print prompt and exit before LLM call. | `false` |
| `--verbose`, `-v` | Show extra grounding details. | `false` |
| `--batch-state` | Batch JSON recovery ledger path. | `reports/batch_progress.json` |
| `--yes` | Skip confirmation. | `false` |
| `--format` | `text` or JSON Lines `json`. | `text` |
| `--no-color` | Suppress terminal styles. | `false` |

## Providers and credentials

Create a private local credentials file once:

```bash
cp .env.example .env
```

PowerShell equivalent:

```powershell
Copy-Item .env.example .env
```

POCArchitect loads `.env` from the current directory without overwriting an
existing environment variable. Set only the key for your real cloud provider:

| Provider | Real-run command | `.env` setting |
|---|---|---|
| xAI | `pocarchitect --url <URL> --provider xai` | `XAI_API_KEY` |
| OpenAI | `pocarchitect --url <URL> --provider openai` | `OPENAI_API_KEY` |
| Groq | `pocarchitect --url <URL> --provider groq` | `GROQ_API_KEY` |
| Local endpoint | `pocarchitect --url <URL> --provider local` | None |

Check provider readiness without generating a report:

```bash
pocarchitect preflight --provider openai
pocarchitect preflight --provider xai
pocarchitect preflight --provider groq
pocarchitect preflight --provider local --base-url http://localhost:11434/v1
```

For a local OpenAI-compatible endpoint such as Ollama:

```bash
ollama serve
ollama pull qwen2.5-coder:32b
pocarchitect --url <AUTHORIZED_GITHUB_URL> --provider local --model qwen2.5-coder:32b
```

See [the local-provider guide](ollama-setup-guide.md) for setup and limitations.

## Batch commands and recovery

Create `batch_urls.txt`, one URL per line:

```text
https://github.com/example/first-poc
https://github.com/example/second-poc
```

Run it interactively:

```bash
pocarchitect --batch batch_urls.txt --provider openai
```

The default ledger is `reports/batch_progress.json`; completed URLs are skipped
on a later run while failed URLs remain retryable. Isolate jobs with a custom
ledger and inspect it:

```bash
pocarchitect --batch batch_urls.txt --provider openai --batch-state reports/customer-a-state.json
pocarchitect batch-status --batch-state reports/customer-a-state.json
```

Reset a ledger; its old contents are moved to a timestamped backup:

```bash
pocarchitect batch-reset --batch-state reports/customer-a-state.json
```

For a previously authorized scheduled run:

```bash
pocarchitect --batch batch_urls.txt --provider openai --batch-state reports/nightly.json --yes --no-color
```

## Automation and JSON output

Use JSON Lines only for the main command and `preflight`:

```bash
pocarchitect preflight --offline --format json --no-color
pocarchitect --url <AUTHORIZED_GITHUB_URL> --no-ingest --dry-run --format json --no-color
```

`batch-status` and `batch-reset` currently produce human-readable output.

Example Bash gate:

```bash
set -euo pipefail
pocarchitect preflight --provider openai --format json --no-color
pocarchitect --url <AUTHORIZED_GITHUB_URL> --provider openai --yes --no-color
```

Example PowerShell gate:

```powershell
$ErrorActionPreference = 'Stop'
pocarchitect preflight --provider openai --format json --no-color
pocarchitect --url <AUTHORIZED_GITHUB_URL> --provider openai --yes --no-color
```

## Docker commands

Build:

```bash
docker build -t pocarchitect:latest .
```

Help and safe first run:

```bash
docker run --rm pocarchitect:latest --help
docker run --rm pocarchitect:latest --url https://github.com/example/poc --no-ingest --dry-run --no-color
```

Interactive cloud run on Bash/Zsh:

```bash
docker run --rm -it \
  --env-file .env \
  -v "$(pwd)/reports:/reports" \
  pocarchitect:latest \
  --url <AUTHORIZED_GITHUB_URL> --provider openai
```

PowerShell version:

```powershell
docker run --rm -it --env-file .env -v "${PWD}/reports:/reports" pocarchitect:latest --url <AUTHORIZED_GITHUB_URL> --provider openai
```

Batch input and persisted reports/ledger:

```bash
docker run --rm -it \
  --env-file .env \
  -v "$(pwd)/reports:/reports" \
  -v "$(pwd)/batch_urls.txt:/batch_urls.txt" \
  pocarchitect:latest \
  --batch /batch_urls.txt --provider openai
```

The image runs as non-root `pocuser`; ensure the mounted host `reports`
directory is writable. Consult [the Docker guide](docker-guide.md) for details.

## Development and documentation commands

Install developer tooling:

```bash
python -m pip install -r requirements-dev.txt
```

Run checks:

```bash
pytest
ruff check .
black --check .
mypy pocarchitect
pip-audit
```

Regenerate generated CLI/configuration documentation after editing command
metadata:

```bash
python scripts/generate_docs.py
```

Bash-oriented repository scripts:

```bash
./verify.sh
./test-full.sh
```

`verify.sh` includes dry-run checks. `test-full.sh` makes real OpenAI calls and
may consume credits; review its settings first. Use these scripts from Bash,
WSL, Git Bash, Linux, or macOS rather than native PowerShell.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `pocarchitect` is not recognized | Activate `.venv`, or use `python -m pocarchitect --help`. |
| Missing/rejected API key | Run `pocarchitect preflight --provider <provider>` and check the matching non-placeholder `.env` setting. |
| Need a no-key test | Use `preflight --offline` or `--no-ingest --dry-run`. |
| GitHub clone fails | Confirm the authorized public URL and network; use `--no-ingest --dry-run` to isolate the CLI. |
| No report appears | Reports are created only after successful real provider calls; dry runs intentionally create none. |
| Batch repeats/does not resume | Check the exact ledger with `pocarchitect batch-status --batch-state <path>`. |
| Need a fresh batch retry | Run `pocarchitect batch-reset --batch-state <path>`; it creates a timestamped backup. |
| Docker cannot write reports | Create a writable host `reports` directory and mount it at `/reports`. |
| Local connection refused | Start the local service, then run `preflight --provider local --base-url <URL>`. |

For metadata-derived details, see [CLI Reference](cli-reference.md) and
[Configuration Reference](configuration-reference.md).
