#!/usr/bin/env python3
"""
POCArchitect Pre-Flight Checker
Companion script for https://github.com/rikterskale/POCArchitect-AI-Agent

Run this after:
1. git clone + cd POCArchitect-AI-Agent
2. pip install -e .
3. (Optional) Create .env with your API key

It validates the FULL environment so you never hit a runtime surprise.
"""

import sys
import os
import subprocess
from pathlib import Path
import importlib.util

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

console = Console()

# ====================== CONFIG ======================
REQUIRED_PYTHON = (3, 9)
REQUIRED_DEPS = [
    "typer",
    "rich",
    "openai",
    "httpx",
    "dotenv",  # python-dotenv
]
PACKAGE_NAME = "pocarchitect"
PROMPT_FILENAME = "POC_Architect_Prompt.md"
ENV_KEY_NAMES = ["XAI_API_KEY", "OPENAI_API_KEY"]


def check_python_version() -> tuple[bool, str]:
    current = sys.version_info[:2]
    ok = current >= REQUIRED_PYTHON
    msg = f"Python {current[0]}.{current[1]}"
    if ok:
        return True, f"✅ {msg} (≥{REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]})"
    return False, f"❌ {msg} — upgrade to Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+"


def check_dependency(dep: str) -> tuple[bool, str]:
    try:
        importlib.import_module(dep)
        return True, f"✅ {dep}"
    except ImportError:
        return False, f"❌ {dep} — not installed (run pip install -e .)"


def check_pocarchitect_package() -> tuple[bool, str]:
    try:
        import pocarchitect
        version = getattr(pocarchitect, "__version__", "0.1.0")
        return True, f"✅ pocarchitect package (v{version})"
    except ImportError:
        return False, "❌ pocarchitect package — run `pip install -e .`"


def check_cli_command() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["pocarchitect", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and "POCArchitect" in result.stdout:
            return True, "✅ pocarchitect CLI command available"
        return False, "❌ CLI command failed"
    except (subprocess.SubprocessError, FileNotFoundError):
        return False, "❌ `pocarchitect` not found in PATH (run `pip install -e .` and reactivate venv if needed)"


def check_prompt_file() -> tuple[bool, str]:
    prompt_path = Path.cwd() / PROMPT_FILENAME
    if prompt_path.exists():
        return True, f"✅ {PROMPT_FILENAME} found"
    script_dir = Path(__file__).parent
    prompt_path = script_dir / PROMPT_FILENAME
    if prompt_path.exists():
        return True, f"✅ {PROMPT_FILENAME} found"
    return False, f"❌ {PROMPT_FILENAME} missing — critical for the agent!"


def check_api_key() -> tuple[bool, str]:
    for key_name in ENV_KEY_NAMES:
        if os.getenv(key_name):
            return True, f"✅ {key_name} found in environment (or .env — now auto-loaded by CLI)"
    
    env_file = Path.cwd() / ".env"
    if env_file.exists():
        content = env_file.read_text(encoding="utf-8", errors="ignore")
        for key_name in ENV_KEY_NAMES:
            if any(line.strip().startswith(f"{key_name}=") for line in content.splitlines()):
                return True, f"✅ {key_name} found in .env (will be auto-loaded)"
    
    return False, f"❌ No API key — set {ENV_KEY_NAMES[0]} in .env or pass --api-key"


def check_output_directory_writable() -> tuple[bool, str]:
    reports_dir = Path.cwd() / "reports"
    try:
        reports_dir.mkdir(parents=True, exist_ok=True)
        test_file = reports_dir / ".preflight_test"
        test_file.touch()
        test_file.unlink()
        return True, "✅ ./reports/ is writable"
    except Exception as e:
        return False, f"❌ Cannot write to ./reports/ — {e}"


def main():
    console.print(Panel.fit(
        "[bold green]POCArchitect Pre-Flight Checker[/]\n"
        "[dim]Validating your full offensive-security AI agent environment[/]",
        border_style="green"
    ))

    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", lambda: (all(check_dependency(d)[0] for d in REQUIRED_DEPS), "See table below")),
        ("Package", check_pocarchitect_package),
        ("CLI Command", check_cli_command),
        ("System Prompt", check_prompt_file),
        ("API Key", check_api_key),
        ("Output Directory", check_output_directory_writable),
    ]

    table = Table(title="Environment Validation", show_header=True, header_style="bold cyan")
    table.add_column("Check", style="dim")
    table.add_column("Status", justify="left")

    all_passed = True

    for name, check_func in checks:
        passed, msg = check_func()
        if not passed:
            all_passed = False
        table.add_row(name, msg)

    console.print(table)

    if all_passed:
        console.print(Panel.fit(
            "[bold green]✅ Environment is PERFECTLY ready![/]\n"
            "You can now run:\n"
            "  pocarchitect --url https://github.com/... --provider xai",
            border_style="green"
        ))
    else:
        console.print(Panel.fit(
            "[bold red]❌ Some checks failed. Fix the red items above then re-run this script.[/]",
            border_style="red"
        ))
        sys.exit(1)


if __name__ == "__main__":
    main()
