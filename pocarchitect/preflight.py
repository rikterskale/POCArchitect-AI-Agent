#!/usr/bin/env python3
import importlib
import json
import os
import shutil
import subprocess  # nosec B404 - controlled diagnostic subprocesses are required by preflight
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

from dotenv import dotenv_values
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import (
    DEFAULT_LOCAL_BASE_URL,
    DEFAULT_PROVIDER,
    PROVIDER_KEY_NAMES,
    default_output_dir,
)
from .output import event_payload

console = Console()

ENV_KEY_NAMES = list(PROVIDER_KEY_NAMES.values())

REQUIRED_DEPS = ["typer", "rich", "openai", "dotenv", "tenacity"]

DIAGNOSTIC_CODES = {
    "Python >=3.10": "PYTHON_VERSION",
    "Git executable": "GIT_MISSING_OR_UNUSABLE",
    "CLI command": "CLI_UNAVAILABLE",
    "System prompt": "PROMPT_ASSET_MISSING",
    "Output directory": "OUTPUT_NOT_WRITABLE",
    "Provider readiness": "PROVIDER_CHECK_SKIPPED",
    "Local endpoint": "LOCAL_ENDPOINT_UNAVAILABLE",
}


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
        return True, "OK: Installed"
    except ImportError:
        return False, "FAIL: Missing"


def check_api_key(provider: str | None = None) -> tuple[bool, str]:
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


def check_local_endpoint(base_url: str | None = None) -> tuple[bool, str]:
    """Verify that the selected OpenAI-compatible local endpoint can list models."""
    endpoint = (base_url or DEFAULT_LOCAL_BASE_URL).rstrip("/")
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False, f"FAIL: Local endpoint must use an http(s) URL: {endpoint}"
    try:
        with urlopen(  # nosec B310 - scheme and network location are validated above
            f"{endpoint}/models", timeout=3
        ) as response:
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


def check_git_command() -> tuple[bool, str]:
    git = shutil.which("git")
    if git is None:
        return False, "FAIL: Git executable not found"
    try:
        # nosec B603 - executable comes from shutil.which("git")
        result = subprocess.run(  # nosec B603
            [git, "--version"],
            capture_output=True,
            check=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False, "FAIL: Git executable is not runnable"
    return True, f"OK: {result.stdout.strip() or 'Git is runnable'}"


def check_output_directory_writable(
    output_dir: Path | None = None,
) -> tuple[bool, str]:
    out_dir = output_dir or default_output_dir()
    try:
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
            # nosec B603, B607 - fixed module/CLI diagnostic commands
            subprocess.run(cmd, capture_output=True, check=True)  # nosec B603, B607
            return True, f"OK: Available via: {' '.join(cmd[:3])}".strip()
        except (OSError, subprocess.CalledProcessError):
            continue
    return False, "FAIL: Not found"


def main(
    require_api_key: bool = True,
    offline: bool = False,
    provider: str = DEFAULT_PROVIDER,
    base_url: str | None = None,
    output_dir: Path | None = None,
    output_format: str = "text",
    no_color: bool = False,
    require_git: bool = True,
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
    table.add_column("Fix", style="yellow")
    results = []

    def add_row(check: str, status: str, ok: bool = True, fix: str = "") -> None:
        remediation = "" if ok else fix
        code = DIAGNOSTIC_CODES.get(check)
        if check.startswith("Dependency: "):
            code = "DEPENDENCY"
        if check.startswith("API key ("):
            code = "PROVIDER_CREDENTIAL"
        results.append(
            {
                "check": check,
                "code": code or "PREFLIGHT_CHECK",
                "status": status,
                "remediation": remediation,
            }
        )
        table.add_row(check, status, remediation or "—")

    has_failure = False

    install_hint = f'{sys.executable} -m pip install -e ".[all]"'

    # Python version
    py_ok = sys.version_info >= (3, 10)
    status = "OK" if py_ok else "FAIL"
    if not py_ok:
        has_failure = True
    add_row(
        "Python >=3.10",
        status,
        ok=py_ok,
        fix="Install Python 3.10+ and recreate the virtual environment.",
    )

    # Dependencies
    for dep in REQUIRED_DEPS:
        ok, msg = check_dependency(dep)
        if not ok:
            has_failure = True
        add_row(f"Dependency: {dep}", msg, ok=ok, fix=f"Run: {install_hint}")

    if require_git:
        ok, msg = check_git_command()
        if not ok:
            has_failure = True
        add_row(
            "Git executable",
            msg,
            ok=ok,
            fix="Install Git, reopen the terminal, and rerun preflight.",
        )
    else:
        add_row("Git executable", "OK: Not required for this command", ok=True)

    # CLI command
    ok, msg = check_cli_command()
    if not ok:
        has_failure = True
    add_row(
        "CLI command",
        msg,
        ok=ok,
        fix=f"Reinstall the package: {install_hint}",
    )

    # Prompt file
    ok, msg = check_prompt_file()
    if not ok:
        has_failure = True
    add_row(
        "System prompt",
        msg,
        ok=ok,
        fix="Run from the repository root, or reinstall so package data is present.",
    )

    # Provider credentials/readiness are only required when a provider call is intended.
    if require_api_key and not offline:
        if provider == "local":
            ok, msg = check_local_endpoint(base_url)
            add_row(
                "Local endpoint",
                msg,
                ok=ok,
                fix="Start the local server (e.g. `ollama serve`) or pass --base-url.",
            )
        else:
            ok, msg = check_api_key(provider)
            key_name = PROVIDER_KEY_NAMES[provider]
            add_row(
                f"API key ({provider})",
                msg,
                ok=ok,
                fix=(
                    f"Run `pocarchitect setup`, or set {key_name} in your environment "
                    "or a local .env file."
                ),
            )
        if not ok:
            has_failure = True
    else:
        add_row("Provider readiness", "OK: Not required for offline checks")

    # Output directory
    ok, msg = check_output_directory_writable(output_dir)
    if not ok:
        has_failure = True
    add_row(
        "Output directory",
        msg,
        ok=ok,
        fix="Pass --output-dir <writable-folder> or fix folder permissions.",
    )

    if output_format == "json":
        console.print(
            json.dumps(
                event_payload(
                    "preflight",
                    "Preflight failed." if has_failure else "Preflight passed.",
                    diagnostic_version=1,
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
        console.print("[bold green]OK: All configured preflight checks passed.[/]")


if __name__ == "__main__":
    main()
