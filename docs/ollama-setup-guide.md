# Ollama Setup Guide for POCArchitect (Beginner-Friendly – April 2026)

This is a complete, standalone HOWTO for offensive security researchers who want to run local, uncensored LLMs with POCArchitect.

- **No cloud API keys needed.**
- **Zero refusals on exploit code, shellcode, C2 implants, or red-team techniques.**

## Why Ollama + POCArchitect?

- Completely private (nothing leaves your machine)
- Free forever
- Best models for exploit writing & threat analysis
- Works perfectly with the `--provider local` support we added to POCArchitect

---

## 1. Prerequisites

### Hardware (minimum)

- 16 GB RAM (32 GB+ recommended)
- GPU with at least 12 GB VRAM for 32B models (NVIDIA/AMD/Apple Silicon)
- Or just CPU (slower but works)

### Operating System

- Windows 10/11
- macOS 13+
- Linux (Ubuntu 22.04+ recommended)

### Software

- Git (already installed if you cloned the repo)
- Python 3.9+ (you already have this for POCArchitect)

---

## 2. Install Ollama (2 minutes)

### Windows

1. Go to https://ollama.com/download
2. Download and run `OllamaSetup.exe`
3. Follow the installer (it adds Ollama to your PATH automatically)

### macOS

```bash
brew install ollama
# or download from https://ollama.com/download
```

### Linux (Ubuntu/Debian)

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Verify installation

```bash
ollama --version
```

You should see something like `ollama version 0.4.x`

---

## 3. Recommended Models for Offensive Security (2026)

Run these exact commands (copy-paste one at a time):

```bash
# BEST OVERALL for exploit writing & PoC analysis (recommended)
ollama pull qwen2.5-coder:32b-uncensored

# OR the newer Qwen3 variant if available
ollama pull qwen3-coder:32b-uncensored

# Best for deep attack chain reasoning
ollama pull deepseek-r1:32b

# Most obedient ("never refuses" anything)
ollama pull dolphin-qwen2:32b

# Purpose-built red-team model (very popular)
ollama pull f0rc3ps/nu11secur1tyAI
```

**Tip:** Start with the first one (`qwen2.5-coder:32b-uncensored`). It's the sweet spot for POCArchitect.

---

## 4. Start Ollama Server

Keep this running in a separate terminal:

```bash
ollama serve
```

You'll see output like:

```
2026/04/02 16:45:12 Listening on http://127.0.0.1:11434
```

---

## 5. Ollama Pre-Flight Checker (New Script)

Create a new file called `ollama_preflight.py` in your repo root and paste this entire script:

```python
#!/usr/bin/env python3
"""
Ollama Pre-Flight Checker for POCArchitect
Run this BEFORE using --provider local
"""

import sys
import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

OLLAMA_URL = "http://localhost:11434"
TEST_MODEL = "qwen2.5-coder:32b-uncensored"   # change if you use a different model


def check_ollama_running() -> tuple[bool, str]:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/version", timeout=3)
        if r.status_code == 200:
            return True, f"✅ Ollama server is running (v{r.json().get('version', 'unknown')})"
        return False, "❌ Ollama responded but not healthy"
    except requests.exceptions.ConnectionError:
        return False, "❌ Ollama is NOT running (run `ollama serve`)"


def check_model_available() -> tuple[bool, str]:
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/show",
            json={"name": TEST_MODEL},
            timeout=5
        )
        if r.status_code == 200:
            return True, f"✅ Model '{TEST_MODEL}' is pulled and ready"
        return False, f"❌ Model '{TEST_MODEL}' not found (run `ollama pull {TEST_MODEL}`)"
    except Exception as e:
        return False, f"❌ Error checking model: {e}"


def run_test_prompt() -> tuple[bool, str]:
    try:
        payload = {
            "model": TEST_MODEL,
            "messages": [{"role": "user", "content": "Say 'POCArchitect local test successful' in one sentence."}],
            "stream": False,
            "options": {"temperature": 0.0}
        }
        r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=15)
        if r.status_code == 200:
            response = r.json()["message"]["content"]
            return True, f"✅ Test prompt worked!\n   Response: {response.strip()}"
        return False, f"❌ Test prompt failed (status {r.status_code})"
    except Exception as e:
        return False, f"❌ Test prompt error: {e}"


def main():
    console.print(Panel.fit(
        "[bold green]Ollama Pre-Flight Checker for POCArchitect[/]\n"
        "[dim]Making sure your local LLM is ready for red-team use[/]",
        border_style="green"
    ))

    checks = [
        ("Ollama Server", check_ollama_running),
        ("Recommended Model", check_model_available),
        ("Live Test Prompt", run_test_prompt),
    ]

    table = Table(title="Ollama Validation", show_header=True, header_style="bold cyan")
    table.add_column("Check", style="dim")
    table.add_column("Status", justify="left")

    all_passed = True

    for name, func in checks:
        passed, msg = func()
        if not passed:
            all_passed = False
        table.add_row(name, msg)

    console.print(table)

    if all_passed:
        console.print(Panel.fit(
            "[bold green]✅ OLLAMA IS PERFECTLY READY![/]\n"
            "You can now use POCArchitect with --provider local",
            border_style="green"
        ))
    else:
        console.print(Panel.fit(
            "[bold red]❌ Fix the issues above, then re-run this script.[/]",
            border_style="red"
        ))
        sys.exit(1)


if __name__ == "__main__":
    main()
```

Make it executable and run it:

```bash
python ollama_preflight.py
```

---

## 6. POCArchitect Usage Examples (Local LLM)

Once the preflight passes, use these commands:

```bash
# Recommended: Best offsec model
pocarchitect --url https://github.com/user/exploit-repo \
  --provider local \
  --base-url http://localhost:11434/v1 \
  --model qwen2.5-coder:32b-uncensored

# With batch file
pocarchitect --url example_usage/batch_urls.txt \
  --provider local \
  --base-url http://localhost:11434/v1 \
  --model qwen2.5-coder:32b-uncensored

# Disable ingestion if you want to test pure LLM behavior
--no-ingest
```

You can add any of the usual flags:

```bash
--temperature 0.0 --risk-level Critical --target-os Linux --verbose
```

---

## 7. Common Errors & Fixes

| Error | Fix |
|-------|-----|
| Connection refused | Run `ollama serve` in another terminal |
| Model not found | Run `ollama pull <model-name>` |
| Out of memory | Use a smaller model (14B instead of 32B) or add `--num-gpu 0` in Ollama |
| Slow generation | Use quantized version: `qwen2.5-coder:32b-q4_K_M` |
| Permission issues on Linux | `sudo usermod -aG docker $USER` then reboot |

---

## 8. Bonus Tips for Power Users

- **List all models:** `ollama list`
- **Remove unused models:** `ollama rm <model>`
- **Run multiple models at once** (Ollama supports it)
- **Use LM Studio or SillyTavern** if you want a GUI

---

You now have a complete local offsec LLM setup that works perfectly with POCArchitect.
