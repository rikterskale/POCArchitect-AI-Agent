# POCArchitect-AI-Agent Architecture

## Overview

**POCArchitect** is an AI-powered CLI tool that transforms raw Proof-of-Concept (PoC) URLs — GitHub repositories, raw code pastes, security advisories, or blog posts — into **high-quality, reproducible Markdown blueprints** optimized for red teamers and penetration testers.

The core philosophy is **zero hallucination**: instead of letting the LLM guess exploit details, the tool fetches actual source code and artifacts, then feeds them into a carefully engineered system prompt. The result is a consistent, operator-ready report containing build instructions, execution playbook, risk assessment, and an annotated weaponized artifact.

### Key Design Goals
- Accuracy over speed (source code is read, not summarized from blogs)
- Multi-LLM support with consistent output structure
- Minimal dependencies and easy local execution
- Support for both interactive CLI and prompt-only workflows (e.g., Cursor, Claude Projects)
- Batch processing for scaling across multiple PoCs
- Strong error handling and clear user feedback

---

## High-Level Flow

```
    A[User Input: URL or batch file] --> B[Preflight Checker]
    B --> C[Fetch PoC Content]
    C --> D[Extract Source Code & Artifacts]
    D --> E[Build Structured Prompt]
    E --> F[LLM Call\n(xAI / OpenAI / Claude / Gemini / compatible)]
    F --> G[Generate Markdown Report]
    G --> H[Save to ./reports/]
```

## Step-by-Step Process

### Input Handling
Single URL or path to a text file containing multiple URLs (batch mode). CLI argument parsing with --url, --provider, --model, --output-dir, etc.

### Preflight Checker (preflight_checker.py)
Validates Python version, API keys, dependencies, and environment readiness. Early failure with clear guidance.

### PoC Fetching
Detects URL type (GitHub repo, raw file, advisory, blog). Clones/downloads relevant code, READMEs, and supporting files. Focuses intelligently on exploit-related content.

### Prompt Construction
Loads the master system prompt from POC_Architect_Prompt.md. Injects fetched source code, file tree, and metadata. Enforces strict output structure.

### LLM Orchestration
Supports multiple providers: xAI (SuperGrok / Grok models — recommended), OpenAI, Anthropic Claude, Google Gemini, and any OpenAI-compatible endpoint.

### Report Generation
Produces standardized Markdown with:

- Metadata & PoC summary
- Build/Setup instructions
- Execution playbook (step-by-step commands)
- Risk assessment (impact, prerequisites, detection)
- Annotated weaponized artifact

Batch runs also generate an index.md.

### Output
Saved to ./reports/ (timestamped or named by PoC). Human-readable and immediately usable.

---

## Component Breakdown

- **pocarchitect/cli.py** — Main entry point. Handles argument parsing, orchestrates the pipeline, and manages output.
- **preflight_checker.py** — Standalone environment and API key validation.
- **POC_Architect_Prompt.md** — Core system prompt enforcing structure and zero-hallucination rules.
- **POCArchitect_Example_Report.md** — Living example of ideal output format.
- **tests/** — Growing test suite covering preflight, report structure, and prompt building.

---

## Error Handling & Robustness

POCArchitect is designed to be resilient when dealing with unpredictable real-world PoC sources. The architecture emphasizes early failure with clear messaging rather than silent or cryptic errors.

### Core Error Handling Principles
- **Fail Fast & Informative**: Issues are caught as early as possible.
- **Graceful Degradation**: Partial results are provided when full processing isn't possible.
- **User-Friendly Messages**: Every error includes actionable guidance.
- **Zero Hallucination Safety**: Process aborts before the LLM call if critical source code cannot be fetched.

### Error Handling Layers

#### Preflight Checker
Validates Python version, required API keys, and basic environment. Provides clear colored messages on failure.

#### Input Validation
Checks URL format, batch file readability, and argument consistency.

#### Fetching Layer
Handles common failures: unreachable URLs, git clone errors, rate limits, large repos, unsupported formats. Returns specific, helpful error messages.

#### LLM Client Layer
Catches authentication errors, rate limiting, and provider-specific issues with clear feedback.

#### Report Generation
Validates that the LLM output contains all required sections. Warns the user if structure appears incomplete.

### Current Robustness Features
- Timeout handling on network operations
- Detailed logging support via --verbose
- Exception chaining to preserve original context
- Early validation to prevent expensive LLM calls on bad input

### Planned Improvements
- Retry mechanism with exponential backoff
- Smart fallback (fetch README + key files if full clone fails)
- Token usage estimation before calling LLM
- Structured error output (JSON mode for automation)
- Caching layer for previously fetched PoCs

---

## Extensibility Points

- Adding new LLM providers via client abstraction
- Custom report templates (Jinja2 planned)
- New fetcher plugins for additional URL types
- Output formats (HTML/PDF planned)

---

## Technology Stack

- **Language**: Python 3.9+
- **Packaging**: pyproject.toml with editable install
- **LLM Clients**: Official SDKs for supported providers
- **Fetching**: Git + requests (BeautifulSoup where needed)
- **Output**: Pure Markdown

---

## Limitations & Design Trade-offs

- Token usage can be high on large repositories
- Depends on LLM context window size and quality
- Currently CLI-focused (web UI or daemon mode planned)
- No built-in sandboxing — users run generated PoCs at their own risk

---

## Future Architecture Directions

- Modular pipeline with clear interfaces per stage
- Caching layer for fetched repos and LLM responses
- Automated quality evaluation framework
- HTML export with syntax highlighting
- Integration hooks for Nuclei, Metasploit, etc.

---

Last Updated: April 02, 2026

Version: 0.x (Early Stage)

Contributions welcome! See CONTRIBUTING.md (when added) or open issues for architecture discussions.
