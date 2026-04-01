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

---

## 🚀 Quick Start (Recommended)

# 1. Install the CLI
git clone (https://github.com/rikterskale/POCArchitect-AI-Agent.git)

cd POCArchitect-AI-Agent

pip install -e .          # installs the `pocarchitect` command

## Usage examples:
### Single PoC
pocarchitect --url https://github.com/some/exploit --provider xai --api-key xai-xxx --model grok-4

### Batch mode
pocarchitect --url example_usage/batch_urls.txt --provider xai --api-key xai-xxx

### Full help
pocarchitect --help
All output goes to ./reports/ (or your --output-dir).

### 2. Run it
pocarchitect --url https://github.com/some/exploit \
             --provider xai \
             --api-key xai-XXXXXXXXXXXXXXXX \
             --model grok-4

That’s it. The report lands in POCArchitect_Report_YYYY-MM-DD.md.

### CLI Usage
# Single URL
pocarchitect --url <URL> --provider xai --api-key <key>

# Batch mode
pocarchitect --url batch_urls.txt --provider openai --api-key <key>

# Full options
pocarchitect --help

Flags

- url → Single URL or path to batch_urls.txt (one URL per line)
- provider → xai or openai (default: xai)
- api-key → Your API key
- model → e.g. grok-4, gpt-5-turbo, claude-3-5-sonnet-20241022
- output-dir → Custom output folder (default: current directory)
- temperature → Default 0.0 (recommended for reproducibility)

Prompt-Only Mode (No CLI)
- If you prefer manual use in Grok / ChatGPT / Claude:

Copy the entire content of POC_Architect_Prompt.md
- Paste it as the System Prompt
- Send a single URL or the contents of batch_urls.txt as the user message

Example Output
- See example_usage/ for real generated reports.
- Example filename:
  POCArchitect_CVE-2024-21413-Outlook-RCE.md

POCArchitect-AI-Agent/
├── pocarchitect/
│   ├── __init__.py
│   └── cli.py
├── POC_Architect_Prompt.md          # ← your existing prompt (unchanged)
├── pyproject.toml
├── README.md
├── requirements.txt                 # optional, pyproject.toml is enough
└── example_usage/

Why This Exists
Red teamers and pentesters waste hours turning messy POCs into usable artifacts. POCArchitect does it in seconds with military-grade consistency.
Star the repo if you find it useful — more features (HTML export, auto-deobfuscation, Dockerized targets) are coming.

Made with 🔥 for the offensive-security community.





