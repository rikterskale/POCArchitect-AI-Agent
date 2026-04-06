#!/usr/bin/env python3
import sys
import os
import subprocess
import importlib
from pathlib import Path
from dotenv import dotenv_values
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

# ── Supported providers only (synced with cli.py) ─────────────────────
ENV_KEY_NAMES = [
    "XAI_API_KEY",
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
]

REQUIRED_DEPS = [
    "typer", "rich", "openai", "dotenv", "git", "tenacity"
]


def _is_valid_key_value(value: str | None) -> bool:
    if value is None:
        return False
    cleaned = value.strip()
    placeholders = {
        "",
        "your_key_here",
        "your-api-key-here",
        "changeme",
        "<your_key>",
        "<api_key>",
    }
    return cleaned.lower() not in placeholders


def check_dependency(name: str) -> tuple[bool, str]:
    try:
        importlib.import_module(name)
        return True, "✓ Installed"
    except ImportError:
        return False, "✗ Missing"

def check_api_key() -> tuple[bool, str]:
    env_path = Path.cwd() / ".env"
    env_file_values = dotenv_values(env_path) if env_path.exists() else {}

    for key in ENV_KEY_NAMES:
        env_value = os.getenv(key)
        file_value = env_file_values.get(key)
        if _is_valid_key_value(env_value):
            return True, f"✓ {key} in environment"
        if _is_valid_key_value(file_value):
            return True, f"✓ {key} in .env"
    return False, "✗ No API key found"

def check_prompt_file() -> tuple[bool, str]:
    prompt_candidates = [
        Path.cwd() / "pocarchitect" / "POC_Architect_Prompt.md",
        Path(__file__).parent / "POC_Architect_Prompt.md",
    ]
    for p in prompt_candidates:
        if p.exists():
            return True, f"✓ Found at {p.name}"
    return False, "✗ Prompt file missing"

def check_output_directory_writable() -> tuple[bool, str]:
    try:
        out_dir = Path("/reports") if Path("/.dockerenv").exists() else Path.cwd() / "reports"
        out_dir.mkdir(parents=True, exist_ok=True)
        test_file = out_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
        return True, f"✓ {out_dir} writable"
    except Exception:
        return False, "✗ Output directory not writable"


def check_cli_command() -> tuple[bool, str]:
    candidates = [
        [sys.executable, "-m", "pocarchitect", "--help"],
        ["pocarchitect", "--help"],
    ]
    for cmd in candidates:
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return True, f"✓ Available via: {' '.join(cmd[:3])}".strip()
        except Exception:
            continue
    return False, "✗ Not found"

def main():
    console.print(Panel("[bold green]POCArchitect Preflight Check[/bold green]", expand=False))

    table = Table(title="Preflight Results")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="green")

    has_failure = False

    # Python version
    py_ok = sys.version_info >= (3, 9)
    status = "✓" if py_ok else "✗"
    if not py_ok:
        has_failure = True
    table.add_row("Python >=3.9", status)

    # Dependencies
    for dep in REQUIRED_DEPS:
        ok, msg = check_dependency(dep)
        if not ok:
            has_failure = True
        table.add_row(f"Dependency: {dep}", msg)

    # CLI command
    ok, msg = check_cli_command()
    if not ok:
        has_failure = True
    table.add_row("CLI command", msg)

    # Prompt file
    ok, msg = check_prompt_file()
    if not ok:
        has_failure = True
    table.add_row("System prompt", msg)

    # API key
    ok, msg = check_api_key()
    if not ok:
        has_failure = True
    table.add_row("API key", msg)

    # Output directory
    ok, msg = check_output_directory_writable()
    if not ok:
        has_failure = True
    table.add_row("Output directory", msg)

    console.print(table)

    if has_failure:
        console.print("[bold red]❌ Preflight failed. Fix the issues above.[/]")
        sys.exit(1)
    else:
        console.print("[bold green]✅ All checks passed! You are ready to run POCArchitect.[/]")

if __name__ == "__main__":
    main()