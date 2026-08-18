# POCArchitect Architecture

## Overview

POCArchitect is a Python CLI that turns a supplied PoC URL into a Markdown
analysis request for a selected LLM provider. It can shallow-clone public GitHub
repositories and include selected source files as grounding. Non-GitHub URLs and
failed GitHub clones use explicitly labeled URL-only context.

Grounding is an input aid, not proof of report accuracy. The tool loads a
packaged prompt, builds grounding context, redacts recognized secret patterns,
asks for transfer confirmation, sends the request to the configured provider,
and saves the provider response with provenance metadata.

## Authoritative runtime entry points

`pyproject.toml` maps the installed `pocarchitect` command to
`pocarchitect.cli:app`, and `python -m pocarchitect` imports the same app through
`pocarchitect/__main__.py`. The only CLI and preflight implementations are
`pocarchitect/cli.py` and `pocarchitect/preflight.py`; the former divergent root
`cli.py` and `preflight.py` copies were retired. Maintainers should not recreate
root-level runtime copies.

## High-level flow

```text
URL or batch file
  -> automatic provider-aware preflight (real runs only)
  -> grounding context and outcome
  -> redaction and transfer preview
  -> operator confirmation
  -> provider request (up to three attempts; 60-second client timeout)
  -> report plus provenance metadata
  -> resolved output directory
```

`--dry-run` bypasses **all automatic preflight checks**, constructs the
provider-facing prompt, and exits before a provider call or report write. Text
mode prints a compact summary unless `--full` is supplied; JSON output includes
the full prompt. Use `pocarchitect preflight --offline` when installation checks
are also needed.

## Core components

| Component | Location | Responsibility |
|---|---|---|
| CLI entry point and orchestration | `pocarchitect/cli.py` | Argument parsing, output events, single and batch workflows |
| Shared runtime defaults | `pocarchitect/config.py` | Provider keys/models, local endpoint, labels, and output-path resolution |
| Preflight checks | `pocarchitect/preflight.py` | Python, imports, Git, CLI, prompt, provider readiness, and resolved output path |
| Batch state | `pocarchitect/state.py` | Versioned load, atomic writes, summaries, and recoverable reset |
| System prompt | `pocarchitect/POC_Architect_Prompt.md` | Provider instructions and report structure |
| Grounding and report saving | `pocarchitect/cli.py` | Clone/selection, ingestion outcomes, metadata, and body hash |

## Guided and novice-facing surfaces

- `setup` is an interactive terminal wizard. It writes a selected cloud key
  only to the current directory's `.env`, or checks a supplied local endpoint,
  then offers a safe dry run.
- `config` reports effective provider-key sources with masked values plus
  default models/output settings.
- The main command accepts `owner/repo` shorthand, validates GitHub repository
  shapes early, and supports paired `--include-mitigations/--no-mitigations`.
- Text dry runs default to a bounded summary; `--full` prints the complete
  prompt. `--open` asks the operating system to open a completed report.
- Interactive real calls use a spinner, and interactive real batches use a
  progress bar with elapsed time and ETA. JSON/non-terminal output remains
  event-based.
- The ingestion preview may show an approximate input-cost hint for models with
  a configured estimate. It is not a quote or billing guarantee.

## Preflight boundaries

Standalone and automatic preflight check:

1. Python 3.10 or newer.
2. Imports for `typer`, `rich`, `openai`, `dotenv`, and `tenacity`.
3. A runnable Git executable.
4. `python -m pocarchitect --help` or the installed console command.
5. The packaged system prompt.
6. For a real cloud run, the selected provider's non-placeholder key; for a
   local run, an HTTP request to `<base-url>/models`.
7. Write access to the same resolved report directory used by the real run.

An explicit `--output-dir` is passed to automatic preflight. The default resolver
uses `/reports` when `/.dockerenv` exists or `IN_DOCKER` is set; otherwise it
uses `reports/` under the current directory.

Preflight does not clone a repository, send the full prompt, create a report,
test local chat completions, or establish model quality/resource sufficiency.

## Grounding outcomes and clone-failure fallback

`build_grounding_context` returns content plus one ingestion outcome:

| Metadata value | Meaning |
|---|---|
| `disabled` | `--no-ingest` intentionally disabled grounding |
| `url-only-non-github` | The URL host is not GitHub and no clone was attempted |
| `url-only-ingestion-failed` | GitHub clone or later ingestion failed; warning/URL context remains |
| `github-shallow-clone` | The depth-one GitHub clone completed |

On a real run, a clone failure emits `WARNING: Ingestion failed (...)` and the
CLI exits before any provider call. The operator must fix ingestion and retry,
or explicitly rerun with `--no-ingest` when URL-only analysis is acceptable.
The `url-only-ingestion-failed` outcome is therefore available for diagnostics
and dry runs; it is not a provider-backed fallback path for real runs.

## Grounding file-selection rules

The current implementation walks the temporary clone in filesystem order and
selects candidates whose filename contains a keyword **or** whose suffix is in
the extension set. This order is implementation-defined; no completeness claim
is made.

| Rule | Current value |
|---|---|
| Filename keywords | `readme`, `exploit`, `payload`, `shell`, `poc`, `index`, `attack`, `main`, `vuln`, `trigger`, `scan`, `app`, `setup`, `install`, `dockerfile`, `makefile`, `requirements`, `config`, `manifest` |
| Extensions | `.py`, `.sh`, `.ps1`, `.yml`, `.yaml`, `.json`, `.md`, `.txt`, `.bat`, `.cmd`, `.cpp`, `.c`, `.go`, `.rs` |
| Per-file size exclusion | Files over 250,000 bytes are skipped |
| Per-file content limit | 7,500 characters, followed by a truncation marker |
| Transfer cap | First 25 matching readable files |
| Excluded directory | `.git` |

## Report provenance

Successful provider responses are written as Markdown with YAML-like front
matter containing `project`, `source_url`, `provider`, `model`, `prompt_asset`,
`generated_at`, `ingestion`, `grounding_files_selected`, and
`content_sha256`. `ingestion` is the outcome above, not an inference from the
operator's flags. `grounding_files_selected` is zero for disabled/URL-only
outcomes and the number of files included for a successful clone.

## Batch behavior

Batch input ignores blank lines and full-line comments whose trimmed content
starts with `#`; inline comments are not removed. Every eligible dry-run URL is
previewed. Interactive real batches show progress and ETA. Real successes and
failures are written atomically to the version-2 ledger. Processing continues
after an item failure, then the command exits 1 after its summary when any item
failed. A zero exit therefore means no processed item failed; consumers may
also inspect `batch_complete.failed` or the ledger.

## Provider defaults

| Provider | Default model |
|---|---|
| `xai` | `grok-3` |
| `openai` | `gpt-4o` |
| `groq` | `llama-3.1-70b-versatile` |
| `local` | `qwen2.5-coder:14b` |

The OpenAI SDK is used for all four choices. Prompt portability references to
Claude or Gemini do not add CLI provider choices; another OpenAI-compatible
service must be supplied through `local` and `--base-url`.

## Current limitations

- The supported command interface is the CLI; there is no HTTP/API server. The
  `WorkflowEngine` module is also a supported Python integration API for
  workflow clients, as documented in the finding-driven workflow guide.
- Private GitHub authentication is not configured by the project.
- No clone cache or source-completeness guarantee exists.
- Provider output and copied commands require operator review.
- The tool does not execute cloned source and supplies no sandbox for report content.

**Documented version:** 0.2.0
