#!/usr/bin/env python3
import importlib
import json
import os
import subprocess
import sys
from urllib.error import URLError
from urllib.request import urlopen
from pathlib import Path
from typing import Optional

from dotenv import dotenv_values
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .output import event_payload

console = Console()

# ── Supported providers only (synced with cli.py) ─────────────────────
PROVIDER_KEY_NAMES = {
    "xai": "XAI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "groq": "GROQ_API_KEY",
}
ENV_KEY_NAMES = list(PROVIDER_KEY_NAMES.values())
DEFAULT_LOCAL_BASE_URL = "http://localhost:11434/v1"

REQUIRED_DEPS = ["typer", "rich", "openai", "dotenv", "tenacity"]


def _is_valid_key_value(value: Optional[str]) -> bool:
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
        return True, "OK: Installed"
    except ImportError:
        return False, "FAIL: Missing"


def check_api_key(provider: Optional[str] = None) -> tuple[bool, str]:
    """Check only the selected cloud provider, or all providers for legacy checks."""
    env_path = Path.cwd() / ".env"
    env_file_values = dotenv_values(env_path) if env_path.exists() else {}

    keys = ENV_KEY_NAMES if provider is None else [PROVIDER_KEY_NAMES[provider]]
    for key in keys:
        env_value = os.getenv(key)
        file_value = env_file_values.get(key)
        if _is_valid_key_value(env_value):
            return True, f"OK: {key} in environment"
        if _is_valid_key_value(file_value):
            return True, f"OK: {key} in .env"
    return False, "FAIL: No API key found"


def check_local_endpoint(base_url: Optional[str] = None) -> tuple[bool, str]:
    """Verify that the selected OpenAI-compatible local endpoint can list models."""
    endpoint = (base_url or DEFAULT_LOCAL_BASE_URL).rstrip("/")
    try:
        with urlopen(f"{endpoint}/models", timeout=3) as response:
            if 200 <= response.status < 300:
                return True, f"OK: Local endpoint ready at {endpoint}"
    except (OSError, URLError) as error:
        return (
            False,
            f"FAIL: Local endpoint unavailable at {endpoint} ({error.reason if isinstance(error, URLError) else error})",
        )
    return False, f"FAIL: Local endpoint returned an unexpected response at {endpoint}"


def check_prompt_file() -> tuple[bool, str]:
    prompt_candidates = [
        Path.cwd() / "pocarchitect" / "POC_Architect_Prompt.md",
        Path(__file__).parent / "POC_Architect_Prompt.md",
    ]
    for p in prompt_candidates:
        if p.exists():
            return True, f"OK: Found at {p.name}"
    return False, "FAIL: Prompt file missing"


def check_output_directory_writable() -> tuple[bool, str]:
    try:
        out_dir = (
            Path("/reports") if Path("/.dockerenv").exists() else Path.cwd() / "reports"
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        test_file = out_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
        return True, f"OK: {out_dir} writable"
    except OSError as error:
        return (
            False,
            f"FAIL: {out_dir} is not writable ({error}); use --output-dir <writable-folder>",
        )


def check_cli_command() -> tuple[bool, str]:
    candidates = [
        [sys.executable, "-m", "pocarchitect", "--help"],
        ["pocarchitect", "--help"],
    ]
    for cmd in candidates:
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return True, f"OK: Available via: {' '.join(cmd[:3])}".strip()
        except Exception:
            continue
    return False, "FAIL: Not found"


def main(
    require_api_key: bool = True,
    offline: bool = False,
    provider: str = "xai",
    base_url: Optional[str] = None,
    output_format: str = "text",
    no_color: bool = False,
):
    global console
    console = Console(no_color=no_color)
    if output_format == "text":
        console.print(
            Panel("[bold green]POCArchitect Preflight Check[/bold green]", expand=False)
        )

    table = Table(title="Preflight Results")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="green")
    results = []

    def add_row(check: str, status: str) -> None:
        results.append({"check": check, "status": status})
        table.add_row(check, status)

    has_failure = False

    # Python version
    py_ok = sys.version_info >= (3, 9)
    status = "OK" if py_ok else "FAIL"
    if not py_ok:
        has_failure = True
    add_row("Python >=3.9", status)

    # Dependencies
    for dep in REQUIRED_DEPS:
        ok, msg = check_dependency(dep)
        if not ok:
            has_failure = True
        add_row(f"Dependency: {dep}", msg)

    # CLI command
    ok, msg = check_cli_command()
    if not ok:
        has_failure = True
    add_row("CLI command", msg)

    # Prompt file
    ok, msg = check_prompt_file()
    if not ok:
        has_failure = True
    add_row("System prompt", msg)

    # Provider credentials/readiness are only required when a provider call is intended.
    if require_api_key and not offline:
        if provider == "local":
            ok, msg = check_local_endpoint(base_url)
            add_row("Local endpoint", msg)
        else:
            ok, msg = check_api_key(provider)
            add_row(f"API key ({provider})", msg)
        if not ok:
            has_failure = True
    else:
        add_row("Provider readiness", "OK: Not required for offline checks")

    # Output directory
    ok, msg = check_output_directory_writable()
    if not ok:
        has_failure = True
    add_row("Output directory", msg)

    if output_format == "json":
        console.print(
            json.dumps(
                event_payload(
                    "preflight",
                    "Preflight failed." if has_failure else "Preflight passed.",
                    provider=provider,
                    offline=offline,
                    checks=results,
                ),
                sort_keys=True,
            ),
            markup=False,
            highlight=False,
            soft_wrap=True,
        )
    else:
        console.print(table)

    if has_failure:
        if output_format == "text":
            console.print(
                "[bold red]FAIL: Preflight failed.[/] Review the failed rows above, then "
                "rerun `python -m pocarchitect preflight --offline`."
            )
        sys.exit(1)
    elif output_format == "text":
        console.print(
            "[bold green]OK: All checks passed! You are ready to run POCArchitect.[/]"
        )


if __name__ == "__main__":
    main()
