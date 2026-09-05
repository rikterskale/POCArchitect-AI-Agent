#!/usr/bin/env python3
"""
Ollama Pre-Flight Checker for POCArchitect
Run this BEFORE using --provider local
"""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

OLLAMA_URL = "http://localhost:11434"
TEST_MODEL = "qwen2.5-coder:14b"  # Practical default for a developer laptop


def check_ollama_running() -> tuple[bool, str]:
    try:
        status, data = request_json("GET", "/api/version", timeout=3)
        if status == 200:
            return (
                True,
                f"✅ Ollama server is running (v{data.get('version', 'unknown')})",
            )
        return False, "❌ Ollama responded but not healthy"
    except (OSError, ValueError) as e:
        return False, f"❌ Ollama server check failed: {e}"


def check_model_available() -> tuple[bool, str]:
    try:
        status, _ = request_json("POST", "/api/show", {"name": TEST_MODEL}, timeout=5)
        if status == 200:
            return True, f"✅ Model '{TEST_MODEL}' is pulled and ready"
        return (
            False,
            f"❌ Model '{TEST_MODEL}' not found (run `ollama pull {TEST_MODEL}`)",
        )
    except (OSError, ValueError) as e:
        return False, f"❌ Error checking model: {e}"


# (#12) Test the OpenAI-compatible endpoint that POCArchitect actually uses
def check_openai_compatible_endpoint() -> tuple[bool, str]:
    try:
        payload = {
            "model": TEST_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": "Say 'POCArchitect local test successful' in one sentence.",
                }
            ],
            "temperature": 0.0,
        }
        status, data = request_json("POST", "/v1/chat/completions", payload, timeout=30)
        if status == 200:
            response_text = (
                data.get("choices", [{}])[0].get("message", {}).get("content", "")
            )
            return (
                True,
                f"✅ OpenAI-compatible endpoint works!\n   Response: {response_text.strip()}",
            )
        return False, f"❌ OpenAI-compatible endpoint failed (status {status})"
    except (OSError, ValueError, IndexError) as e:
        return False, f"❌ OpenAI-compatible endpoint error: {e}"


def request_json(
    method: str,
    path: str,
    payload: dict | None = None,
    *,
    timeout: float,
) -> tuple[int, dict]:
    """Make one bounded JSON request using only the Python standard library."""
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{OLLAMA_URL}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if body else {},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return int(response.status), json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        return error.code, {}
    except URLError as error:
        raise OSError(error.reason) from error


def main():
    console.print(
        Panel.fit(
            "[bold green]Ollama Pre-Flight Checker for POCArchitect[/]\n"
            "[dim]Running three bounded Ollama checks[/]",
            border_style="green",
        )
    )

    checks = [
        ("Ollama Server", check_ollama_running),
        ("Recommended Model", check_model_available),
        ("OpenAI-Compatible Endpoint (/v1)", check_openai_compatible_endpoint),
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
        console.print(
            Panel.fit(
                "[bold green]✅ THE THREE LISTED OLLAMA CHECKS PASSED[/]\n"
                f"Base URL: {OLLAMA_URL} | Model: {TEST_MODEL}\n"
                "This did not test POCArchitect's full prompt, report generation, "
                "response quality, or host resource sufficiency.",
                border_style="green",
            )
        )
        return 0
    else:
        console.print(
            Panel.fit(
                "[bold red]❌ Fix the issues above, then re-run this script.[/]",
                border_style="red",
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
