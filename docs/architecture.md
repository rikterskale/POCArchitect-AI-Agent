# POCArchitect Architecture

## Overview

**POCArchitect** is a Python CLI that turns a supplied PoC URL into a Markdown analysis request for a selected LLM provider. It can shallow-clone public GitHub repositories to include selected source files as grounding; non-GitHub URLs receive limited, URL-only grounding.

Grounding is an input aid, not a guarantee of report accuracy. The tool loads a packaged prompt, optionally clones a public GitHub repository, redacts recognized secret patterns, asks for transfer confirmation, sends the request to the configured provider, and saves the provider response as a Markdown report with metadata.

### Implemented boundaries
- GitHub grounding uses `git clone --depth 1 --single-branch` with a 90-second timeout; it does not execute cloned source.
- A non-GitHub URL is accepted but is not cloned for grounding.
- `--dry-run` prints the provider-facing prompt and skips the provider-readiness preflight.
- Real source transfer requires interactive confirmation, or `--yes` in a noninteractive job.
- Batch state is written atomically so completed URLs can be skipped on resume.

---

## High-Level Flow
User Input (URL or batch file)
↓
Provider-aware Preflight (real runs only)
↓
Grounding Context (smart clone + file extraction)
↓
Prompt Construction (system prompt + operator preferences)
↓
LLM Call (up to three attempts; 60-second client timeout)
↓
Markdown Report Generation
↓
Save to ./reports/ (or /reports in Docker)

---

## Core Components

| Component                        | Location                                 | Responsibility |
|----------------------------------|------------------------------------------|----------------|
| CLI Entry Point & Orchestration  | `pocarchitect/cli.py`                    | All argument parsing, pipeline control, batch/single mode |
| Preflight Checks                 | `pocarchitect/preflight.py`              | Environment validation (runs automatically) |
| System Prompt                    | `pocarchitect/POC_Architect_Prompt.md`   | Defines exact report structure and zero-hallucination rules |
| Grounding Logic                  | `pocarchitect/cli.py` (`build_grounding_context`) | Shallow GitHub clone plus keyword/extension file selection |
| LLM Client                       | `pocarchitect/cli.py` (`get_llm_response`) | Provider support, API-key resolution, retries, timeout |
| Report Saving                    | `cli.py`                                 | Timestamped reports saved to output directory |

---

## Key Implementation Details

- **CLI orchestration**: `pocarchitect/cli.py` owns parsing and the single/batch workflow; batch-state operations are isolated in `pocarchitect/state.py`.
- **Batch Mode**: Accepts `.txt` files via `--batch`, processes each URL sequentially, generates one report per URL.
- **Operator Controls**: `--risk-level`, `--target-os`, and `--include-mitigations` are included in the provider request. The public CLI currently has no flag that sets `include_mitigations` to false.
- **Resilience**: LLM calls use `tenacity` (3 retries with exponential backoff) + 60-second timeout.
- **Docker Awareness**: Default output directory becomes `/reports` when `/.dockerenv` exists or `IN_DOCKER` is set.
- **API Key Handling**: Automatic resolution from `.env` for xAI, OpenAI, and Groq.
- **Provider-Specific Models**: Default model adjusts per provider (e.g., `grok-3` for xAI, `gpt-4o` for OpenAI).

---

## Technology Stack

- **Language**: Python 3.10+
- **CLI Framework**: Typer + Rich
- **LLM Client**: OpenAI SDK (used for xAI, OpenAI, Groq, and OpenAI-compatible local endpoints)
- **Grounding**: `git` subprocess (shallow clone)
- **Retries**: tenacity
- **Config**: python-dotenv
- **Packaging**: pyproject.toml + setuptools

---

## Limitations (Current)

- The tool has no API server or library API; the supported interface is the CLI.
- Source selection is limited to at most 25 matching files, with individual files truncated at 7,500 characters.
- There is no built-in cache of cloned repositories.
- Generated reports and provider output require operator review; no sandbox is provided for material copied from a report.

---

**Reviewed version:** 0.2.0
