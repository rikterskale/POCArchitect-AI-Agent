# POCArchitect Architecture

## Overview

**POCArchitect** is a focused, production-ready CLI tool that turns any Proof-of-Concept URL (primarily GitHub repositories) into a clean, reproducible, operator-ready Markdown blueprint.

The design philosophy is **zero hallucination through grounding**: the tool performs a shallow `git clone`, intelligently extracts key files, injects them into a high-quality system prompt, and returns a structured report containing tactical summary, deep dive, risk assessment, build instructions, execution playbook, weaponized artifact, and MITRE mapping.

### Current Design Goals (Met)
- Accurate grounding via real source code (not just READMEs)
- Batch mode via `--batch` flag (processes `.txt` files with one URL per line)
- Operator controls fully wired (`--risk-level`, `--target-os`, `--include-mitigations`)
- Automatic preflight checks on every run
- Robust LLM calls with retries and timeouts
- Smart Docker support (reports automatically land in mounted volume)
- Minimal, clean dependency list

---

## High-Level Flow
User Input (URL or batch file)
↓
Automatic Preflight (preflight.py)
↓
Grounding Context (smart clone + file extraction)
↓
Prompt Construction (system prompt + operator preferences)
↓
LLM Call (with retry + 60s timeout)
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
| Grounding Logic                  | `cli.py` (`build_grounding_context`)     | Shallow clone + improved keyword/extension file selection |
| LLM Client                       | `cli.py` (`get_llm_response`)            | Provider support, API key resolution, retries, timeout |
| Report Saving                    | `cli.py`                                 | Timestamped reports saved to output directory |

---

## Key Implementation Details

- **Monolithic but clean**: All core logic lives in `cli.py` (intentional simplicity for a CLI tool).
- **Batch Mode**: Accepts `.txt` files via `--batch`, processes each URL sequentially, generates one report per URL.
- **Operator Controls**: `--risk-level`, `--target-os`, and `--include-mitigations` are now injected into every prompt.
- **Resilience**: LLM calls use `tenacity` (3 retries with exponential backoff) + 60-second timeout.
- **Docker Awareness**: Default output directory automatically becomes `/reports` when running inside a container.
- **API Key Handling**: Automatic resolution from `.env` for xAI, OpenAI, and Groq.
- **Provider-Specific Models**: Default model adjusts per provider (e.g., `grok-3` for xAI, `gpt-4o` for OpenAI).

---

## Technology Stack

- **Language**: Python 3.9+
- **CLI Framework**: Typer + Rich
- **LLM Client**: OpenAI SDK (unified for xAI, OpenAI, Groq, local Ollama)
- **Grounding**: GitPython (shallow clone)
- **Retries**: tenacity
- **Config**: python-dotenv
- **Packaging**: pyproject.toml + setuptools

---

## Limitations (Current)

- Still a single-file CLI (no separate service layer)
- Token usage can be high on very large repositories
- No built-in caching of cloned repos (yet)
- No sandboxing of generated exploits (user responsibility)

---

**Last Updated**: April 03, 2026  
**Version**: 0.2.0 (Post-Audit)

The architecture is intentionally pragmatic: a reliable, maintainable CLI that delivers high-quality results today while remaining easy to extend.
