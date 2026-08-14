# POCArchitect AI Agent

> Turn messy PoCs into clean, reproducible blueprints.

POCArchitect is a command-line tool that creates a structured Markdown analysis report from an authorized Proof-of-Concept (PoC) URL. For GitHub repository URLs, it can shallow-clone and select source files as grounding before sending a redacted preview to the selected LLM provider.

It does not execute the retrieved PoC. A report is generated only after a real provider call succeeds; report content depends on the selected provider and the available source material.

## Features

- Guided first-run `setup` wizard and a `config` command that shows effective settings (keys masked)
- Shallow GitHub clone and source-file selection for grounding
- `owner/repo` shorthand and early URL validation
- Batch mode (`--batch batch_urls.txt`) with a live progress bar and ETA
- Operator controls: `--risk-level`, `--target-os`, `--include-mitigations/--no-mitigations`, `--no-ingest`
- Provider-aware preflight checks with actionable fix hints; `--dry-run` skips provider readiness checks
- Ingestion preview with a rough cost estimate before any provider call
- Cloud providers (`xai`, `openai`, `groq`) and a local OpenAI-compatible endpoint (`local`)
- Docker image with a writable `/reports` volume
- Retry logic + timeouts on LLM calls; fast, friendly errors for unknown models
- Reports print their absolute path with an optional `--open`, plus a short preview
- Shell completion (`--install-completion`), `--dry-run` (summary, or `--full`), and `--verbose`

## Start here

If you are new to terminals, Git, or Python, begin with the standalone [Novice Usability Guide](docs/NOVICE_USABILITY_GUIDE.md). It includes Windows PowerShell and Bash setup paths, a safe first run that makes no provider call, expected results, and repair steps.

After installing, the quickest guided path is the interactive wizard, which stores a provider key in a local `.env` and checks readiness:

```bash
pocarchitect setup
```

From the repository root, a safe first run is:

```bash
python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --format json --no-color
```

This command does not clone the example repository, contact an LLM provider, create a report, or require a credential. It prints JSON Lines events ending with `"event": "dry_run"`.

For installation and an offline readiness check, follow the guide or run:

```bash
python -m pip install -e ".[all]"
python -m pocarchitect preflight --offline --format json --no-color
```

`preflight --offline` verifies Python, installed packages, the package entry point, the prompt asset, and a writable default output directory. A real cloud-provider run additionally requires the matching provider key.

## Supported-platform matrix

| Platform/path | Status | Notes |
|---|---|---|
| Linux Bash | Validated in CI | CI exercises Ubuntu with Python 3.10–3.13. |
| Windows PowerShell | Partially validated | The safe CLI workflow was reviewed in an existing Windows virtual environment; native Windows CI is not configured. |
| WSL/Git Bash | Not separately validated | Treat as an alternative shell, not proof of native Windows support. |
| Docker Desktop/Linux Docker | Validated in CI | CI builds the image and runs its `--help` smoke test; mount a writable host directory to `/reports` for reports. |

## Batch progress and recovery

Batch runs write a resumable JSON ledger to `reports/batch_progress.json` by default. Pass `--batch-state path\to\state.json` to choose another location. Completed URLs are skipped on the next run; failed URLs remain eligible for retry. Inspect or reset a ledger with the `batch-status` and `batch-reset` subcommands (see the [CLI Reference](docs/cli-reference.md)).

## Common command options

| Option | Description | Default |
|---|---|---|
| `--url`, `-u` | Single PoC GitHub URL (or `owner/repo` shorthand) | Required (or use `--batch`) |
| `--batch`, `-b` | Path to `.txt` file with multiple URLs | None |
| `--provider`, `-p` | LLM provider | `xai` |
| `--model`, `-m` | Model name | Provider-specific (e.g., `grok-3`) |
| `--temperature`, `-t` | Provider temperature | `0.2` |
| `--risk-level` | Free-text risk label sent to the provider | `High` |
| `--target-os` | Free-text target label sent to the provider | `Linux` |
| `--include-mitigations` / `--no-mitigations` | Include mitigation instructions; use `--no-mitigations` to omit | `true` |
| `--no-ingest` | Skip GitHub grounding | `false` |
| `--dry-run` | Show a prompt summary and exit (no API call); add `--full` for the entire prompt | `false` |
| `--full` | With `--dry-run`, print the entire prompt instead of a summary | `false` |
| `--open` | Open each finished report in the OS default viewer | `false` |
| `--verbose`, `-v` | Extra grounding details | `false` |
| `--batch-state` | Custom resumable batch-ledger path | `reports/batch_progress.json` for batch runs |
| `--format` | Text or JSON Lines output for main runs and `preflight` | `text` |
| `--no-color` | Disable terminal styling | `false` |
| `--version`, `-V` | Show version and exit | — |

Full help:

```bash
pocarchitect --help
```

The canonical CLI and configuration references are generated from the command metadata with:

```bash
python scripts/generate_docs.py
```

## Documentation

- [Novice Usability Guide](docs/NOVICE_USABILITY_GUIDE.md) — installation, safe first use, troubleshooting, cleanup, and update instructions.
- [Command Guide](docs/command-guide.md) — end-to-end Windows, macOS/Linux, provider, batch, automation, Docker, and development commands.
- [CLI Reference](docs/cli-reference.md) — generated option and subcommand reference.
- [Configuration Reference](docs/configuration-reference.md) — provider keys, defaults, precedence, and output settings.
- [Docker Guide](docs/docker-guide.md) — image build, safe runs, provider confirmation, and report mounts.
- [Local OpenAI-Compatible Provider Guide](docs/ollama-setup-guide.md) — Ollama-specific setup notes and limitations.
- [Architecture](docs/architecture.md) — implementation-oriented component overview.
- [Release Readiness Standard](docs/RELEASE_READINESS.md) — the five-pillar new-user readiness gate enforced in CI.
- [Documentation Review Report](docs/DOCUMENTATION_REVIEW_REPORT.md) — traceability matrix and validation record for this review.

## Safety and authorization

Only analyze repositories you are authorized to inspect. GitHub grounding clones a public repository into a temporary directory, then sends selected, redacted source content to the selected provider only after confirmation. `--yes` bypasses the confirmation prompt and is intended only for an already-reviewed, authorized noninteractive job. Provider calls may incur charges under the provider account.

## Update and support

To update a checkout, run `git pull`, reactivate the virtual environment, run `python -m pip install -e ".[all]"`, then rerun the offline preflight. Report problems with the command, operating system, Python version, provider name (never the key), and output from `python -m pocarchitect preflight --offline --format json --no-color` at the [issue tracker](https://github.com/rikterskale/POCArchitect-AI-Agent/issues).

## License

See [LICENSE](LICENSE).
