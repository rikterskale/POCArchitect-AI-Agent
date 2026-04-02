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
