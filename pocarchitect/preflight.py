#!/usr/bin/env python3
"""
POCArchitect Pre-Flight Checker
Companion script for https://github.com/rikterskale/POCArchitect-AI-Agent

Run this after:
1. git clone + cd into the repo
2. pip install -e .[all]
3. Create .env with your API key(s)
"""

import sys
import os
import subprocess
import importlib
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# ====================== CONFIG ======================
REQUIRED_PYTHON = (3, 9)
REQUIRED_DEPS = [
    "typer",
    "rich",
    "openai",
    "httpx",
    "dotenv",
    "git",                    # GitPython (for PoC ingestion / grounding)
]
PACKAGE_NAME = "pocarchitect"
PROMPT_FILENAME = "POC_Architect_Prompt.md"

ENV_KEY_NAMES = [
    "XAI_API_KEY",
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
]


def check_python_version() -> tuple[bool, str]:
    current = sys.version_info[:2]
    ok = current >= REQUIRED_PYTHON
    msg = f"Python {current[0]}.{current[1]}"
    return (True, f"✅ {msg}") if ok else (False, f"❌ {msg} — upgrade to Python 3.9+")


def check_dependency(dep: str) -> tuple[bool, str]:
    try:
        importlib.import_module(dep)
        return True, f"✅ {dep}"
    except ImportError:
        return False, f"❌ {dep} — not installed (run pip install -e .[all])"


def check_pocarchitect_package() -> tuple[bool, str]:
    try:
        import pocarchitect
        version = getattr(pocarchitect, "__version__", "unknown")
        return True, f"✅ pocarchitect v{version}"
    except ImportError:
        return False, "❌ pocarchitect package not found"


def check_cli_command() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["pocarchitect", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True, "✅ CLI command available"
        return False, "❌ CLI command failed"
    except (subprocess.SubprocessError, FileNotFoundError):
        return False, "❌ `pocarchitect` not found in PATH"


def check_prompt_file() -> tuple[bool, str]:
    for base in [Path.cwd(), Path(__file__).parent]:
        if (base / PROMPT_FILENAME).exists():
            return True, f"✅ {PROMPT_FILENAME} found"
    return False, f"❌ {PROMPT_FILENAME} missing (critical!)"


def check_api_key() -> tuple[bool, str]:
    found = [k for k in ENV_KEY_NAMES if os.getenv(k)]
    if found:
        return True, f"✅ API key(s): {', '.join(found)}"

    env_file = Path.cwd() / ".env"
    if env_file.exists():
        content = env_file.read_text(encoding="utf-8", errors="ignore")
        for key in ENV_KEY_NAMES:
            if any(line.strip().startswith(f"{key}=") for line in content.splitlines()):
                return True, f"✅ {key} found in .env"
    return False, "❌ No API key found"


def check_output_directory_writable() -> tuple[bool, str]:
    reports_dir = Path.cwd() / "reports"
    try:
        reports_dir.mkdir(parents=True, exist_ok=True)
        test_file = reports_dir / ".preflight_test.tmp"
        test_file.touch()
        test_file.unlink()
        return True, "✅ ./reports/ is writable"
    except Exception:
        return False, "❌ Cannot write to ./reports/"


def main():
    console.print(Panel.fit(
        "[bold green]POCArchitect Pre-Flight Checker[/bold green]\n"
        "[dim]Validating your full environment before running the AI agent[/dim]",
        border_style="blue"
    ))

    checks = [
        ("Python Version", check_python_version),
        ("pocarchitect Package", check_pocarchitect_package),
        ("CLI Command", check_cli_command),
        ("System Prompt", check_prompt_file),
        ("API Key", check_api_key),
        ("Reports Directory", check_output_directory_writable),
    ]

    table = Table(title="Environment Checks", header_style="bold cyan")
    table.add_column("Check", style="dim", width=28)
    table.add_column("Status", justify="left")

    passed_count = 0
    total_checks = len(checks) + len(REQUIRED_DEPS)

    # Main checks
    for name, check_func in checks:
        passed, msg = check_func()
        if passed:
            passed_count += 1
        table.add_row(name, msg)

    # Individual dependency checks
    for dep in REQUIRED_DEPS:
        passed, msg = check_dependency(dep)
        if passed:
            passed_count += 1
        table.add_row(f"  • {dep}", msg)

    console.print(table)

    # Final Summary Table
    summary = Table(title="Summary", show_header=False)
    summary.add_column("Item", style="bold")
    summary.add_column("Count")
    summary.add_row("Total Checks", str(total_checks))
    summary.add_row("✅ Passed", f"[green]{passed_count}[/green]")
    summary.add_row("❌ Failed", f"[red]{total_checks - passed_count}[/red]")
    console.print(summary)

    if passed_count == total_checks:
        console.print(Panel.fit(
            "[bold green]✅ Environment is PERFECTLY ready![/bold green]\n\n"
            "Quick start:\n"
            "  [bold]pocarchitect --url https://github.com/... --provider xai[/bold]\n\n"
            "Happy hunting! 🔥",
            border_style="green"
        ))
    else:
        console.print(Panel.fit(
            "[bold red]❌ Some checks failed — fix the red items above then re-run.[/bold red]",
            border_style="red"
        ))
        sys.exit(1)


if __name__ == "__main__":
    main()
