# POCArchitect

> **Forging the blueprints of digital domination.**  
> **I don't write exploits — I architect empires of proof-of-concept that turn defenses into dust.**

**POCArchitect** is a senior offensive-security AI agent that takes **any** POC URL (GitHub repo, raw code, advisory, blog post) and instantly outputs a **complete, reproducible, zero-guesswork Markdown blueprint**.

Every report contains build instructions, execution playbook, risk assessment, and a fully annotated weaponized artifact — accurate enough for a competent operator to run it with zero external reference.

---

## ✨ Features

- One URL → One perfect Markdown report
- Full build + execution playbook + annotated weaponized code
- Supports **SuperGrok (xAI)**, OpenAI (GPT-4o / GPT-5.x), Claude, Gemini, or any OpenAI-compatible endpoint
- Batch processing (hundreds of URLs → folder of reports + `index.md`)
- Zero hallucination — reads actual source code
- Beautiful, consistent output format every time
- ### Python-side PoC Ingestion (NEW)
- Automatically performs a shallow `git clone --depth 1` on any GitHub repo, scans the file tree, and extracts the most important files (README, exploit code, Dockerfile, payloads, etc.).
- The CLI then injects a clean **GROUNDING CONTEXT** block directly into the LLM prompt.

**Benefits:**
- Zero hallucinations on code structure and content
- Works reliably with *any* provider (including models without browsing tools)
- Faster and cheaper generations
- Graceful fallback for non-GitHub URLs

**New flag:** `--no-ingest` to disable this behavior if needed.

**Benefits:**
- Zero hallucinations on code structure and content
- Works reliably with *any* provider (including models without browsing tools)
- Faster and cheaper generations
- Graceful fallback for non-GitHub URLs

**New flag:** `--no-ingest` to disable this behavior if needed.

---
## 🚀 Installation & Quick Start

### Prerequisites
- Python 3.9+
- xAI (Grok), OpenAI, or any OpenAI-compatible API key

### 1. Install the CLI (Recommended)

```bash
git clone https://github.com/rikterskale/POCArchitect-AI-Agent.git
cd POCArchitect-AI-Agent

# Option 1: Modern (recommended)
pip install -e .

# Option 2: Using requirements.txt
pip install -r requirements.txt
pip install -e .

# Verify
pocarchitect --help

# Alternative (no clone)
pip install git+https://github.com/rikterskale/POCArchitect-AI-Agent.git

# API Key Setup (pick one)
A. Environment variable (recommended)
****POCArchitect now auto-loads `.env`** from the project root.:**
1. Copy the template:
   cp .env.example .env
   Add keys as required

B. Pass on command line
--api-key xai-XXXXXXXXXXXXXXXX

# Usage Examples
Single PoC
pocarchitect \
  --url https://github.com/some/exploit \
  --provider xai \
  --model grok-4

# Batch mode
pocarchitect \
  --url example_usage/batch_urls.txt \
  --provider xai

# Full help
pocarchitect --help

# All generated reports are saved to ./reports/ (or your chosen --output-dir).
```

### Prompt-only mode (no CLI)

Copy the entire content of POC_Architect_Prompt.md as your system prompt and send a URL (or batch_urls.txt content) as the user message

Why This Exists
Red teamers and pentesters waste hours turning messy POCs into usable artifacts. POCArchitect does it in seconds with military-grade consistency.
Star the repo if you find it useful — more features (HTML export, auto-deobfuscation, Dockerized targets) are coming.

Made with 🔥 for the offensive-security community.





