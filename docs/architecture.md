# POCArchitect — AI Agent Architecture

## Overview

**POCArchitect** is an AI-powered CLI tool that transforms raw Proof-of-Concept (PoC) URLs — GitHub repositories, raw code pastes, security advisories, or blog posts — into **high-quality, reproducible Markdown blueprints** optimized for red teamers and penetration testers.

The core philosophy is **zero hallucination**: instead of letting the LLM guess exploit details, the tool fetches actual source code and artifacts, then feeds them into a carefully engineered system prompt. The result is a consistent, operator-ready report containing build instructions, execution playbook, risk assessment, and an annotated weaponized artifact.

### Key Design Goals

- Accuracy over speed (source code is read, not summarized from blogs)
- Multi-LLM support with consistent output structure
- Minimal dependencies and easy local execution
- Support for both interactive CLI and prompt-only workflows (e.g., Cursor, Claude Projects)
- Batch processing for scaling across multiple PoCs

---

## High-Level Flow

```
flowchart TD
    A[User Input: URL or batch file] --> B[Preflight Checker]
    B --> C[Fetch PoC Content]
    C --> D[Extract Source Code & Artifacts]
    D --> E[Build Structured Prompt]
    E --> F[LLM Call\n(xAI / OpenAI / Claude / Gemini / compatible)]
    F --> G[Generate Markdown Report]
    G --> H[Save to ./reports/]
```

---

## Step-by-Step Process

### 1. Input Handling

- Single URL or path to a text file containing multiple URLs (batch mode)
- CLI argument parsing (`--url`, `--provider`, `--model`, `--output-dir`, etc.)

### 2. Preflight Checker (`preflight_checker.py`)

- Validates Python version, API keys, dependencies, and environment readiness
- Early failure with clear guidance instead of cryptic errors

### 3. PoC Fetching

- Detects URL type (GitHub repo, raw file, advisory page, blog, etc.)
- Clones or downloads relevant code, READMEs, scripts, and supporting files
- Handles large repos intelligently (focus on exploit-related files)

### 4. Prompt Construction

- Loads the master system prompt from `POC_Architect_Prompt.md`
- Injects fetched source code, file tree, and metadata
- Structures output with strict sections for reproducibility

### 5. LLM Orchestration

Supports multiple providers:

- **xAI** (SuperGrok / Grok models) — default/recommended
- **OpenAI** (GPT-4o, etc.)
- **Anthropic Claude**
- **Google Gemini**
- Any **OpenAI-compatible** endpoint

Uses provider-specific clients with fallback options.

### 6. Report Generation

Produces a standardized Markdown file with:

- Metadata & PoC summary
- Build/Setup instructions
- Execution playbook (step-by-step commands)
- Risk assessment (impact, prerequisites, detection)
- Annotated weaponized artifact (cleaned + commented code)
- Optional `index.md` for batch runs

### 7. Output

- Saved to `./reports/` (timestamped or named by PoC)
- Human-readable and immediately usable in operations

---

## Component Breakdown

### Core Package (`pocarchitect/`)

- **`cli.py`** — Main entry point. Handles argument parsing, orchestrates the full pipeline, and manages output.
- *(Future modules will include: `fetcher.py`, `llm_client.py`, `prompt_builder.py`, `report_generator.py`, `utils.py`)*

### Key Supporting Files

- **`POC_Architect_Prompt.md`** — The heart of the system. Contains the detailed system instructions that enforce structure, accuracy, and zero-hallucination behavior.
- **`preflight_checker.py`** — Standalone validation script.
- **`requirements.txt` + `pyproject.toml`** — Dependency and packaging configuration.
- **`POCArchitect_Example_Report.md`** — Living example of ideal output.

---

## Data Flow

```
URL → Fetcher → Raw Content + Code → Prompt Builder → LLM → Structured Markdown → File System
```

---

## Extensibility Points

- **Adding new LLM providers:** Extend the client abstraction (planned).
- **Custom report templates:** Future support via Jinja2 or prompt variants.
- **Fetcher plugins:** Easy addition of new URL types (e.g., private Git repos, specific advisory formats).
- **Output formats:** Planned HTML export, JSON intermediate format.

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.9+ |
| Packaging | Modern `pyproject.toml` with editable install |
| LLM Clients | Official SDKs for supported providers |
| Fetching | Git, `requests`, BeautifulSoup (or similar) for web content |
| Output | Pure Markdown (no heavy templating yet) |

---

## Limitations & Design Trade-offs

- Token usage can be high on large repositories (mitigated by smart file selection)
- Depends on LLM quality and context window size
- Currently CLI-focused (web UI or daemon mode planned for future)
- No built-in sandboxing — users run generated PoCs at their own risk

---

## Future Architecture Directions

- Modular pipeline with clear interfaces for each stage
- Caching layer for fetched repos and LLM responses
- Evaluation framework to measure report quality across models
- HTML/PDF export with syntax highlighting
- Integration with tools like Nuclei, Metasploit, or Cobalt Strike

---

> **Last Updated:** April 2026
> **Version:** 0.x (Early Stage)
>
> Contributions welcome! See `CONTRIBUTING.md` (when added) or open issues for architecture discussions.

