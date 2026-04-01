# POCArchitect

> **Forging the blueprints of digital domination.**  
> **I don't write exploits — I architect empires of proof-of-concept that turn defenses into dust.**

**POCArchitect** is a senior offensive-security engineer AI agent that ingests any proof-of-concept (GitHub repo, raw code URL, advisory, or blog post) and outputs a **complete, self-contained, reproducible operational blueprint** in Markdown.

Every report is accurate enough that a competent operator can reproduce the POC with **zero guesswork**.

---

## Features

- One URL = One perfect Markdown report
- Full build instructions, execution playbook, and weaponized artifact
- Works with **SuperGrok (xAI)**, GPT-5.x, Claude 3.5/4, Gemini 2.0, or any OpenAI-compatible API
- Batch processing of hundreds of URLs
- 100% faithful to the original source code — no hallucination

---

## Quick Start (SuperGrok / xAI Recommended)

1. Go to [grok.x.ai](https://grok.x.ai) or use the xAI API
2. Paste the **entire contents** of `POCArchitect_Prompt-FINAL.md` as the **System Prompt**
3. In the user message, paste **a single URL** (or upload `batch_urls.txt`)

Done. You will receive a perfect `POCArchitect_Report_*.md` file.

---

## Full Setup Instructions

### Step 1: Clone This Repo
```bash
git clone https://github.com/YOURUSERNAME/POCArchitect.git
cd POCArchitect

Step 2: Choose Your Platform
Option A — SuperGrok / xAI (Recommended)

Open grok.x.ai → New Chat
Click the system prompt icon (or use API)
Paste the full content of POCArchitect_Prompt-FINAL.md
Save as custom agent (SuperGrok supports persistent agents)

Option B — OpenAI (GPT-5.x / ChatGPT)

Go to chatgpt.com → Custom GPT → Create
Paste POCArchitect_Prompt-FINAL.md into Instructions
Upload the prompt file as a knowledge file

Option C — Claude (Anthropic)

Open Claude.ai → Projects → New Project
Paste the full prompt as System Prompt
Add POCArchitect_Prompt-FINAL.md as a document

Option D — Gemini / Others
Use any OpenAI-compatible endpoint and set the system prompt to the content of POCArchitect_Prompt-FINAL.md.

