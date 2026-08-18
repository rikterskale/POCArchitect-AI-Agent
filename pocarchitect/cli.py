#!/usr/bin/env python3
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
from contextlib import AbstractContextManager, contextmanager, nullcontext
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import urlparse

import typer
from dotenv import dotenv_values, load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

# ── Preflight support ─────────────────────────────────────
from .config import (
    DEFAULT_LOCAL_BASE_URL,
    DEFAULT_MODELS,
    DEFAULT_PROVIDER,
    DEFAULT_RISK_LEVEL,
    DEFAULT_TARGET_OS,
    DEFAULT_TEMPERATURE,
    PROVIDER_KEY_NAMES,
    default_output_dir,
)
from .output import event_payload
from .preflight import main as run_preflight
from .state import (
    BatchStateError,
    load_state,
    reset_state,
    summarize_state,
    write_state,
)

load_dotenv(override=False)

app = typer.Typer(
    name="pocarchitect",
    help="POCArchitect AI Agent - Turn messy PoCs into clean, reproducible blueprints.",
    add_completion=True,
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()
output_format = "text"
no_color_state = False


def configure_output(format_name: str, no_color: bool) -> None:
    """Configure the shared presentation layer before any command emits output."""
    global console, output_format, no_color_state
    output_format = format_name
    no_color_state = no_color
    # Windows consoles default to a legacy code page (cp1252) that cannot encode
    # emoji or box-drawing characters; reconfigure to UTF-8 so output never
    # crashes when piped or redirected. Best-effort and harmless elsewhere.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass
    console = Console(no_color=no_color)


def emit(event: str, message: str, **details: object) -> None:
    """Emit either human-readable text or one stable JSON Lines event."""
    if output_format == "json":
        console.print(
            json.dumps(event_payload(event, message, **details), sort_keys=True),
            markup=False,
            highlight=False,
            soft_wrap=True,
        )
    else:
        console.print(message)


# Known-good models per provider, surfaced when a provider rejects a model name.
KNOWN_MODELS = {
    "xai": ["grok-3", "grok-3-mini", "grok-2"],
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
    "groq": ["llama-3.1-70b-versatile", "llama-3.1-8b-instant"],
    "local": ["qwen2.5-coder:32b", "llama3.1:8b", "(any locally pulled model)"],
}

# Rough input-token prices (USD per 1M input tokens) for a friendly cost hint.
# These are approximate and only used to help a novice gauge order of magnitude;
# actual charges depend on the provider, model, and output length.
MODEL_INPUT_PRICES_PER_MTOK = {
    "gpt-4o": 2.50,
    "gpt-4o-mini": 0.15,
    "gpt-4-turbo": 10.00,
    "grok-3": 3.00,
    "grok-3-mini": 0.30,
    "grok-2": 2.00,
    "llama-3.1-70b-versatile": 0.59,
    "llama-3.1-8b-instant": 0.05,
}


class FatalProviderError(RuntimeError):
    """A provider error that must not be retried (bad model, bad credential)."""


def _looks_like_model_error(message: str) -> bool:
    low = message.lower()
    return (
        ("model" in low and ("not found" in low or "does not exist" in low))
        or "model_not_found" in low
        or "unknown model" in low
        or ("404" in low and "model" in low)
    )


def _looks_like_auth_error(message: str) -> bool:
    low = message.lower()
    return "401" in low or "unauthorized" in low or "invalid api key" in low


def _is_retryable(exc: BaseException) -> bool:
    """Retry transient failures only; permanent errors should fail fast."""
    if isinstance(exc, (typer.Exit, FatalProviderError)):
        return False
    message = str(exc)
    if _looks_like_model_error(message) or _looks_like_auth_error(message):
        return False
    return True


def estimate_cost_usd(model: str, input_tokens: int) -> Optional[float]:
    """Return an approximate USD cost for the input tokens, or None if unknown."""
    price = MODEL_INPUT_PRICES_PER_MTOK.get(model)
    if price is None:
        return None
    return (input_tokens / 1_000_000) * price


def expand_url_shorthand(value: str) -> str:
    """Expand ``owner/repo`` shorthand into a full github.com URL.

    A value that already has a scheme, or that is not a bare ``owner/repo``
    pair, is returned unchanged so existing behavior is preserved.
    """
    candidate = value.strip()
    if "://" in candidate or candidate.startswith("git@"):
        return candidate
    parts = [p for p in candidate.split("/") if p]
    if len(parts) == 2 and " " not in candidate and "." not in parts[0]:
        return f"https://github.com/{parts[0]}/{parts[1]}"
    return candidate


def validate_poc_url(value: str, no_ingest: bool) -> str:
    """Normalize shorthand and reject clearly invalid GitHub URLs early."""
    expanded = expand_url_shorthand(value)
    parsed = urlparse(expanded.strip())
    host = parsed.netloc.lower()
    if host in {"github.com", "www.github.com"} and not no_ingest:
        # Surface a clear, early error instead of a deep git clone failure.
        normalize_github_repo_url(expanded)
    return expanded


def open_in_default_viewer(path: Path) -> bool:
    """Best-effort open of a file in the OS default application."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
        return True
    except Exception:
        return False


def report_digest(content: str, max_lines: int = 8) -> str:
    """Return the first meaningful lines of a report for a quick preview."""
    lines = []
    for raw in content.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        lines.append(stripped)
        if len(lines) >= max_lines:
            break
    return "\n".join(lines)


class _DemoProviderHandler(BaseHTTPRequestHandler):
    """Minimal OpenAI-compatible endpoint used by the credential-free demo."""

    def log_message(self, *_args: object) -> None:
        pass

    def _send(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 — stdlib handler API
        if self.path.endswith("/models"):
            self._send(200, {"object": "list", "data": [{"id": "demo-model"}]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802 — stdlib handler API
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        self._send(
            200,
            {
                "id": "chatcmpl-demo",
                "object": "chat.completion",
                "model": "demo-model",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": (
                                "# POCArchitect Demo Report\n\n"
                                "This credential-free report proves the installed "
                                "provider and report-writing path.\n"
                            ),
                        },
                    }
                ],
            },
        )


@contextmanager
def demo_provider() -> Iterator[str]:
    """Serve a deterministic local response for ``pocarchitect demo``."""
    server = HTTPServer(("127.0.0.1", 0), _DemoProviderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/v1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@app.command("preflight")
def preflight(
    offline: bool = typer.Option(
        False,
        "--offline",
        help="Check installation without requiring an API key or provider access.",
    ),
    provider: Literal["xai", "openai", "groq", "local"] = typer.Option(
        DEFAULT_PROVIDER, "--provider", "-p", help="Provider whose readiness to check."
    ),
    base_url: Optional[str] = typer.Option(
        None, "--base-url", help="OpenAI-compatible local provider endpoint."
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        help="Directory whose report-write access should be checked.",
    ),
    output_format: Literal["text", "json"] = typer.Option(
        "text", "--format", help="Output mode: text or JSON Lines."
    ),
    no_color: bool = typer.Option(
        False, "--no-color", help="Disable ANSI color and style sequences."
    ),
):
    """Run environment preflight checks"""
    run_preflight(
        provider=provider,
        base_url=base_url,
        require_api_key=not offline,
        offline=offline,
        output_dir=output_dir,
        output_format=output_format,
        no_color=no_color,
    )


@app.command("doctor")
def doctor(
    provider: Literal["xai", "openai", "groq", "local"] = typer.Option(
        DEFAULT_PROVIDER, "--provider", "-p", help="Provider whose readiness to check."
    ),
    base_url: Optional[str] = typer.Option(
        None, "--base-url", help="OpenAI-compatible local provider endpoint."
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        help="Directory whose report-write access should be checked.",
    ),
    offline: bool = typer.Option(
        False,
        "--offline",
        help="Skip credentials and endpoint checks; diagnose the local installation only.",
    ),
):
    """Diagnose installation, Git, output, and selected-provider readiness."""
    run_preflight(
        provider=provider,
        base_url=base_url,
        require_api_key=not offline,
        offline=offline,
        output_dir=output_dir,
        output_format=output_format,
        no_color=no_color_state,
    )
    if output_format == "text":
        console.print(
            "[bold green]Doctor complete.[/] If all rows passed, retry your original command."
        )


@app.command("demo")
def demo() -> None:
    """Generate a local demo report without credentials, network, or provider cost."""
    output_dir = Path.cwd() / "reports" / "demo"
    with demo_provider() as base_url:
        run_preflight(
            provider="local",
            base_url=base_url,
            require_api_key=True,
            output_dir=output_dir,
            output_format=output_format,
            no_color=no_color_state,
        )
        process_single_url(
            url="https://github.com/example/poc",
            provider="local",
            api_key=None,
            model="demo-model",
            temperature=0.0,
            base_url=base_url,
            output_dir=output_dir,
            risk_level=DEFAULT_RISK_LEVEL,
            target_os=DEFAULT_TARGET_OS,
            include_mitigations=True,
            no_ingest=True,
            dry_run=False,
            verbose=False,
            confirmed=True,
            open_report=False,
            show_spinner=False,
        )


def load_prompt() -> str:
    try:
        prompt_file = files("pocarchitect") / "POC_Architect_Prompt.md"
        return prompt_file.read_text(encoding="utf-8")
    except Exception as e:
        emit("error", f"Prompt error: {friendly_error_message(e)}")
        raise typer.Exit(1)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:60]


def get_default_output_dir() -> Path:
    return default_output_dir()


@dataclass(frozen=True)
class GroundingResult:
    content: str
    ingestion: Literal[
        "disabled",
        "url-only-non-github",
        "url-only-ingestion-failed",
        "github-shallow-clone",
    ]
    selected_files: int = 0


DEFAULT_BATCH_STATE = Path("reports/batch_progress.json")


def resolve_batch_state_path(explicit: Path) -> Optional[Path]:
    """Find an existing batch ledger, tolerating a different --output-dir.

    Returns the first existing candidate, or None when no ledger exists yet so
    callers can show a friendly 'no batch has been run' message. When the user
    passed a non-default path we honor it verbatim even if it is missing, so an
    explicit typo surfaces plainly rather than silently resolving elsewhere.
    """
    if explicit != DEFAULT_BATCH_STATE:
        return explicit if explicit.exists() else None
    candidates = [
        explicit,
        get_default_output_dir() / "batch_progress.json",
        Path.cwd() / "reports" / "batch_progress.json",
    ]
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.exists():
            return candidate
    return None


def save_report(
    content: str,
    url: str,
    output_dir: Path,
    provider: str,
    model: str,
    grounding: GroundingResult,
    open_report: bool = False,
) -> Path:
    slug = slugify(url.split("/")[-1] or "unknown-poc")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"POCAnalysis_{slug}_{timestamp}.md"
    output_path = output_dir / filename

    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "project": "POCArchitect AI Agent",
        "source_url": url,
        "provider": provider,
        "model": model,
        "prompt_asset": "pocarchitect/POC_Architect_Prompt.md",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ingestion": grounding.ingestion,
        "grounding_files_selected": grounding.selected_files,
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }
    metadata_block = (
        "---\n"
        + "\n".join(f"{key}: {json.dumps(value)}" for key, value in metadata.items())
        + "\n---\n\n"
    )
    output_path.write_text(metadata_block + content, encoding="utf-8")
    absolute_path = output_path.resolve()
    emit(
        "report_saved",
        f"Report saved: {output_path.name}\nLocation: {absolute_path}",
        path=str(output_path),
        absolute_path=str(absolute_path),
    )

    # (#5) Show a short preview so the user sees they got a real result.
    digest = report_digest(content)
    if digest:
        emit("report_digest", f"Preview:\n{digest}", digest=digest)

    # (#4) Optionally open the report in the OS default viewer.
    if open_report:
        if open_in_default_viewer(absolute_path):
            emit("report_opened", "Opened the report in your default viewer.")
        else:
            emit(
                "report_open_failed",
                f"Could not open the report automatically. Open it manually: {absolute_path}",
            )
    return output_path


SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(
        r"(?i)\b(?:[a-z0-9]+_)*(?:api[_ -]?key|access[_ -]?token|secret)\s*[:=]\s*[^\s]+"
    ),
    re.compile(r"(?i)\b(?:sk|xai|gsk)-[A-Za-z0-9_-]{12,}"),
)
PRIVATE_KEY_BLOCK = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    re.DOTALL,
)
KEY_ASSIGNMENT = re.compile(
    r"(?i)(\b(?:[a-z0-9]+_)*(?:api[_ -]?key|access[_ -]?token|secret)\s*[:=]\s*)[^\s]+"
)
PROVIDER_TOKEN = re.compile(r"(?i)\b(?:sk|xai|gsk)-[A-Za-z0-9_-]{12,}")


def detect_sensitive_input(text: str) -> list[str]:
    """Return generic secret categories without echoing matched values."""
    categories = []
    if SECRET_PATTERNS[0].search(text):
        categories.append("private-key material")
    if SECRET_PATTERNS[1].search(text):
        categories.append("key/token assignment")
    if SECRET_PATTERNS[2].search(text):
        categories.append("provider-token format")
    return categories


def redact_sensitive_input(text: str) -> tuple[str, list[str], int]:
    """Redact detected secret values before provider transfer or error persistence."""
    categories = detect_sensitive_input(text)
    redacted, private_count = PRIVATE_KEY_BLOCK.subn("[REDACTED PRIVATE KEY]", text)
    redacted, assignment_count = KEY_ASSIGNMENT.subn(r"\1[REDACTED]", redacted)
    redacted, token_count = PROVIDER_TOKEN.subn("[REDACTED PROVIDER TOKEN]", redacted)
    return redacted, categories, private_count + assignment_count + token_count


def confirm_ingestion(
    source_text: str,
    provider: str,
    model: str,
    confirmed: bool,
) -> str:
    """Preview a redacted transfer and require explicit approval by default."""
    redacted, categories, redaction_count = redact_sensitive_input(source_text)
    classification = "source content" if not categories else ", ".join(categories)
    estimated_tokens = max(1, len(redacted) // 4)
    estimated_cost = estimate_cost_usd(model, estimated_tokens)
    cost_note = (
        f"≈ ${estimated_cost:.4f} (input only, {model})"
        if estimated_cost is not None
        else "cost estimate unavailable for this model"
    )
    emit(
        "ingestion_preview",
        "Ingestion preview: source will be sent to the selected provider after redaction. "
        f"Estimated input cost: {cost_note}.",
        provider=provider,
        model=model,
        classification=classification,
        redaction_count=redaction_count,
        character_count=len(redacted),
        estimated_tokens=estimated_tokens,
        estimated_cost_usd=(
            round(estimated_cost, 6) if estimated_cost is not None else None
        ),
    )
    if confirmed:
        return redacted
    if not sys.stdin.isatty():
        emit(
            "confirmation_required",
            "Confirmation is required in non-interactive mode; review the preview and rerun with --yes.",
        )
        raise typer.Exit(2)
    if not typer.confirm(
        "Send the redacted source content to the selected provider?", default=False
    ):
        emit("cancelled", "No source content was sent to the provider.")
        raise typer.Exit(0)
    return redacted


def friendly_error_message(error: Exception) -> str:
    if isinstance(error, subprocess.TimeoutExpired):
        return (
            "The operation timed out. Check network access or retry with --no-ingest."
        )
    if isinstance(error, FileNotFoundError):
        return "A required file or executable was not found. Check the working directory and rerun preflight --offline."
    if isinstance(error, subprocess.CalledProcessError):
        return "Git failed while ingesting the repository. Confirm the URL is public and valid, then retry."
    message, _, _ = redact_sensitive_input(str(error).strip())
    if _looks_like_model_error(message):
        return (
            "The provider did not recognize the requested model. "
            "Check --model, or omit it to use the provider default."
        )
    if _looks_like_auth_error(message):
        return "The provider rejected the credential. Check the selected provider environment variable without printing the key."
    if "429" in message or "rate limit" in message.lower():
        return "The provider rate limit was reached. Wait and retry, or choose a permitted local provider."
    return (
        message
        or "The operation failed without a diagnostic message. Rerun with --verbose."
    )


def normalize_github_repo_url(poc_url: str) -> tuple[str, str]:
    parsed = urlparse(poc_url.strip())
    host = parsed.netloc.lower()
    if host not in {"github.com", "www.github.com"}:
        raise ValueError("Only github.com URLs are supported for grounding ingestion")

    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) < 2:
        raise ValueError(
            "Expected a GitHub repository URL in the format /<owner>/<repo>"
        )

    owner = path_parts[0]
    repo = path_parts[1]
    if repo.lower().endswith(".git"):
        repo = repo[:-4]

    if not owner or not repo:
        raise ValueError("Could not determine repository owner/name from URL")

    repo_name = f"{owner}/{repo}"
    clone_url = f"https://github.com/{owner}/{repo}.git"
    return repo_name, clone_url


def build_grounding_context(
    poc_url: str, no_ingest: bool = False, verbose: bool = False
) -> GroundingResult:
    if no_ingest:
        return GroundingResult(
            f"PoC URL: {poc_url}\n[Grounding disabled by --no-ingest]",
            "disabled",
        )

    context = ["=== GROUNDING CONTEXT — USE THIS HEAVILY ==="]
    context.append(f"PoC URL: {poc_url}\n")

    parsed = urlparse(poc_url.strip())
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        context.append("Non-GitHub URL — limited analysis.")
        return GroundingResult("\n".join(context), "url-only-non-github")

    try:
        repo_name, clone_url = normalize_github_repo_url(poc_url)

        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_path = Path(tmp_dir) / "poc"
            emit(
                "ingestion_started",
                f"Cloning {repo_name} (shallow)...",
                repository=repo_name,
            )
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--single-branch",
                    clone_url,
                    str(repo_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=90,
                env={
                    "GIT_TERMINAL_PROMPT": "0",
                    "PATH": os.environ.get("PATH", ""),
                },
            )
            emit("ingestion_complete", f"Cloned {repo_name}.", repository=repo_name)

            if verbose:
                emit("grounding", f"Analyzing {repo_name}.", repository=repo_name)

            context.append(f"Repository: {repo_name}")
            context.append("Critical files and content:")

            critical = []
            keywords = [
                "readme",
                "exploit",
                "payload",
                "shell",
                "poc",
                "index",
                "attack",
                "main",
                "vuln",
                "trigger",
                "scan",
                "app",
                "setup",
                "install",
                "dockerfile",
                "makefile",
                "requirements",
                "config",
                "manifest",
            ]
            extensions = {
                ".py",
                ".sh",
                ".ps1",
                ".yml",
                ".yaml",
                ".json",
                ".md",
                ".txt",
                ".bat",
                ".cmd",
                ".cpp",
                ".c",
                ".go",
                ".rs",
            }

            for root, dirs, files_list in os.walk(repo_path):
                if ".git" in dirs:
                    dirs.remove(".git")
                rel_root = Path(root).relative_to(repo_path)
                for file in files_list:
                    file_path = rel_root / file
                    full_path = Path(root) / file

                    if full_path.stat().st_size > 250_000:
                        if verbose:
                            emit("grounding_skip", f"Skipped large file: {file_path}")
                        continue

                    lower_name = file_path.name.lower()
                    if (
                        any(k in lower_name for k in keywords)
                        or Path(file_path).suffix.lower() in extensions
                    ):
                        try:
                            content = full_path.read_text(
                                encoding="utf-8", errors="ignore"
                            )
                            if len(content) > 7500:
                                content = content[:7500] + "\n... [truncated]"
                            critical.append((str(file_path), content))
                        except (OSError, UnicodeError):
                            if verbose:
                                emit(
                                    "grounding_skip",
                                    f"Could not read selected file: {file_path}",
                                )

            if verbose:
                emit(
                    "grounding",
                    f"Found {len(critical)} critical files (showing up to 25).",
                )

            selected = critical[:25]
            for filepath, content in selected:
                lang = Path(filepath).suffix[1:] if Path(filepath).suffix else "text"
                context.append(f"\n--- File: {filepath} ---")
                context.append(f"```{lang}")
                context.append(content.strip())
                context.append("```")

            context.append("\n=== END OF GROUNDING CONTEXT ===\n")
            context.append(
                "MANDATORY: Base your entire report on the files above. Quote real code and techniques. Do not hallucinate."
            )
            return GroundingResult(
                "\n".join(context),
                "github-shallow-clone",
                selected_files=len(selected),
            )

    except (OSError, ValueError, subprocess.SubprocessError) as e:
        context.append(f"WARNING: Ingestion failed ({friendly_error_message(e)}).")
        return GroundingResult("\n".join(context), "url-only-ingestion-failed")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
def get_llm_response(
    provider: str,
    api_key: Optional[str],
    model: str,
    temperature: float,
    base_url: Optional[str],
    system_prompt: str,
    user_message: str,
) -> str:
    p = provider.lower()

    # Resolve API key from environment if not provided (#1: guard against None key for env_map)
    if api_key is None:
        env_var = PROVIDER_KEY_NAMES.get(p)
        if env_var is not None:
            api_key = os.getenv(env_var)

    if p == "local":
        client = OpenAI(
            api_key=api_key or "ollama",
            base_url=base_url or DEFAULT_LOCAL_BASE_URL,
            timeout=60.0,
        )
    elif p in ["xai", "openai", "groq"]:
        base = None
        if p == "xai":
            base = "https://api.x.ai/v1"
        elif p == "groq":
            base = "https://api.groq.com/openai/v1"
        client = OpenAI(api_key=api_key, base_url=base, timeout=60.0)
    else:
        emit("error", f"Unsupported provider: {provider}")
        raise typer.Exit(1)

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
    except Exception as error:  # noqa: BLE001 — normalize provider SDK errors
        message, _, _ = redact_sensitive_input(str(error))
        if _looks_like_model_error(message):
            valid = ", ".join(KNOWN_MODELS.get(p, [])) or "the provider's model list"
            emit(
                "error",
                f"The provider rejected model '{model}'. "
                f"Known-good {p} models: {valid}. "
                "Pass a valid --model, or omit --model to use the provider default.",
                provider=p,
                model=model,
            )
            raise FatalProviderError(f"unknown model: {model}") from error
        raise

    # (#8) Guard against None content
    content = response.choices[0].message.content
    if content is None:
        emit("error", "LLM returned empty content")
        raise typer.Exit(1)
    return content.strip()


def process_single_url(
    url: str,
    provider: str,
    api_key: Optional[str],
    model: str,
    temperature: float,
    base_url: Optional[str],
    output_dir: Path,
    risk_level: str,
    target_os: str,
    include_mitigations: bool,
    no_ingest: bool,
    dry_run: bool = False,
    verbose: bool = False,
    confirmed: bool = True,
    open_report: bool = False,
    dry_run_full: bool = False,
    show_spinner: bool = False,
):
    emit("processing", f"Processing: {url}", url=url)

    system_prompt = load_prompt()
    grounding_result = build_grounding_context(
        url, no_ingest=no_ingest, verbose=verbose
    )
    grounding = grounding_result.content
    if not no_ingest:
        if dry_run:
            grounding, _, _ = redact_sensitive_input(grounding)
        else:
            grounding = confirm_ingestion(grounding, provider, model, confirmed)

    user_message = f"""PoC URL: {url}

{grounding}

Operator Preferences (respect these exactly):
- Risk Level: {risk_level}
- Target OS / Environment: {target_os}
- Include Mitigations: {"Yes" if include_mitigations else "No"}"""

    if dry_run:
        full_prompt = f"--- SYSTEM PROMPT ---\n{system_prompt}\n\n--- USER MESSAGE ---\n{user_message}"
        if output_format == "json":
            emit(
                "dry_run",
                "Dry-run complete; no provider call was made.",
                prompt=full_prompt,
            )
            raise typer.Exit(0)
        console.print(
            "[bold green]🚀 DRY RUN MODE — No LLM call will be made[/bold green]"
        )
        if dry_run_full:
            console.print(
                Panel(
                    full_prompt,
                    title="Full Prompt (Ready for LLM)",
                    border_style="blue",
                    expand=True,
                )
            )
        else:
            # (#8) Default to a compact summary; the whole prompt is huge and
            # overwhelming for a first-time user. --full prints everything.
            prompt_lines = full_prompt.splitlines()
            preview = "\n".join(prompt_lines[:40])
            summary = (
                f"System prompt: {len(system_prompt):,} chars\n"
                f"User message:  {len(user_message):,} chars\n"
                f"Total prompt:  {len(full_prompt):,} chars "
                f"(≈ {max(1, len(full_prompt) // 4):,} tokens)\n"
                f"Lines:         {len(prompt_lines):,}\n\n"
                "First 40 lines shown below. Re-run with --full to see the entire prompt.\n"
                "──────────────────────────────────────────────\n"
                f"{preview}"
            )
            console.print(
                Panel(
                    summary,
                    title="Dry-Run Summary",
                    border_style="blue",
                    expand=True,
                )
            )
        raise typer.Exit(0)

    # (#3) Show a spinner while the provider call blocks (text + interactive only).
    status_cm = (
        console.status(f"Analyzing with {provider}/{model}…", spinner="dots")
        if show_spinner
        else nullcontext()
    )
    try:
        with status_cm:
            result = get_llm_response(
                provider=provider,
                api_key=api_key,
                model=model,
                temperature=temperature,
                base_url=base_url,
                system_prompt=system_prompt,
                user_message=user_message,
            )
    except FatalProviderError:
        # A friendly, actionable message was already emitted; fail without a trace.
        raise typer.Exit(1)

    return save_report(
        result,
        url,
        output_dir,
        provider,
        model,
        grounding_result,
        open_report=open_report,
    )


# ── Batch processing (#2) ────────────────────────────────────────────
def process_batch_file(
    batch_path: Path,
    provider: str,
    api_key: Optional[str],
    model: str,
    temperature: float,
    base_url: Optional[str],
    output_dir: Path,
    risk_level: str,
    target_os: str,
    include_mitigations: bool,
    no_ingest: bool,
    dry_run: bool = False,
    verbose: bool = False,
    state_path: Optional[Path] = None,
    confirmed: bool = True,
    open_report: bool = False,
    dry_run_full: bool = False,
):
    """Read URLs from a text file and process each one sequentially."""
    if not batch_path.exists():
        emit("error", f"Batch file not found: {batch_path}")
        raise typer.Exit(2)

    raw = batch_path.read_text(encoding="utf-8")
    urls = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    if not urls:
        emit("error", "Batch file is empty or contains no valid URLs")
        raise typer.Exit(2)

    emit(
        "batch_started",
        f"Batch mode: {len(urls)} URL(s) from {batch_path.name}",
        total=len(urls),
    )
    processed_count = 0
    success_count = 0
    failure_count = 0
    failed_urls = []
    state_path = state_path or output_dir / "batch_progress.json"
    try:
        state = load_state(state_path)
    except BatchStateError as error:
        emit("error", friendly_error_message(error), state_path=str(state_path))
        raise typer.Exit(2)
    skipped_completed = 0

    def persist_state() -> None:
        write_state(state_path, state)

    # (#12) Live progress bar with ETA for interactive terminals; non-terminal
    # and JSON runs keep the plain per-URL event lines only.
    use_progress = output_format == "text" and not dry_run and console.is_terminal
    progress: Optional[Progress] = None
    task_id: Optional[TaskID] = None
    if use_progress:
        progress = Progress(
            TextColumn("[cyan]Batch[/cyan]"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("elapsed •"),
            TimeRemainingColumn(),
            TextColumn("ETA"),
            console=console,
        )
    progress_cm: AbstractContextManager = progress or nullcontext()

    with progress_cm:
        if progress is not None:
            task_id = progress.add_task("batch", total=len(urls))

        def advance() -> None:
            if progress is not None and task_id is not None:
                progress.advance(task_id)

        for i, url in enumerate(urls, 1):
            if state.get("items", {}).get(url, {}).get("status") == "success":
                skipped_completed += 1
                emit(
                    "batch_skipped",
                    f"Skipping completed URL {i}/{len(urls)}: {url}",
                    url=url,
                )
                advance()
                continue
            processed_count += 1
            emit("batch_item", f"URL {i}/{len(urls)}", url=url, index=i)
            try:
                process_single_url(
                    url=url,
                    provider=provider,
                    api_key=api_key,
                    model=model,
                    temperature=temperature,
                    base_url=base_url,
                    output_dir=output_dir,
                    risk_level=risk_level,
                    target_os=target_os,
                    include_mitigations=include_mitigations,
                    no_ingest=no_ingest,
                    dry_run=dry_run,
                    verbose=verbose,
                    confirmed=confirmed,
                    open_report=open_report,
                    dry_run_full=dry_run_full,
                    show_spinner=False,
                )
                success_count += 1
                state.setdefault("items", {})[url] = {
                    "status": "success",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                persist_state()
            except typer.Exit as e:
                if dry_run:
                    if e.exit_code == 0:
                        success_count += 1
                    else:
                        failure_count += 1
                        failed_urls.append(url)
                        emit(
                            "batch_item_failed",
                            f"Batch dry-run item failed: {url} (exit code {e.exit_code}).",
                            url=url,
                        )
                    advance()
                    continue
                failure_count += 1
                failed_urls.append(url)
                state.setdefault("items", {})[url] = {
                    "status": "failed",
                    "error": f"exit code {e.exit_code}",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                persist_state()
                emit(
                    "batch_item_failed",
                    f"Batch item failed: {url} (exit code {e.exit_code}).",
                    url=url,
                )
                emit("batch_continue", "Continuing to next URL...")
            except Exception as e:
                failure_count += 1
                failed_urls.append(url)
                state.setdefault("items", {})[url] = {
                    "status": "failed",
                    "error": friendly_error_message(e),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                persist_state()
                emit(
                    "batch_item_failed",
                    f"Batch item failed: {url}: {friendly_error_message(e)}",
                    url=url,
                )
                emit("batch_continue", "Continuing to next URL...")
            advance()

    emit(
        "batch_complete",
        f"Batch complete: total={len(urls)} processed={processed_count} "
        f"success={success_count} failed={failure_count} skipped={len(urls) - processed_count} "
        f"resumed={skipped_completed} state={state_path}",
        total=len(urls),
        processed=processed_count,
        success=success_count,
        failed=failure_count,
        skipped=len(urls) - processed_count,
        resumed=skipped_completed,
        state_path=str(state_path),
    )
    if failed_urls:
        emit("batch_failed_urls", "Failed URLs.", urls=failed_urls)
        if output_format == "text":
            for failed_url in failed_urls:
                console.print(f" - {failed_url}")
    if skipped_completed:
        emit(
            "batch_resumed",
            f"Resumed batch: {skipped_completed} completed URL(s) skipped.",
        )
    if failed_urls:
        raise typer.Exit(1)


# ── Main CLI entry point ─────────────────────────────────────────────
@app.command("batch-status")
def batch_status(
    batch_state: Path = typer.Option(
        DEFAULT_BATCH_STATE,
        "--batch-state",
        help="Batch ledger to inspect.",
    ),
):
    """Show a concise, machine-readable summary of batch recovery state."""
    resolved = resolve_batch_state_path(batch_state)
    if resolved is None:
        emit(
            "batch_status_empty",
            "No batch has been run yet (no ledger found). "
            "Run a batch with `--batch <file>` first, or pass --batch-state <path>.",
            state_path=str(batch_state),
        )
        raise typer.Exit(0)
    batch_state = resolved
    try:
        state = load_state(batch_state)
    except BatchStateError as error:
        emit("error", friendly_error_message(error), state_path=str(batch_state))
        raise typer.Exit(2)
    summary = summarize_state(state)
    emit(
        "batch_status",
        "Batch state: "
        f"total={summary['total']} success={summary['success']} "
        f"failed={summary['failed']} unknown={summary['unknown']}",
        state_path=str(batch_state),
        version=state.get("version"),
        **summary,
    )


@app.command("batch-reset")
def batch_reset(
    batch_state: Path = typer.Option(
        Path("reports/batch_progress.json"),
        "--batch-state",
        help="Batch ledger to reset.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        help="Confirm the recoverable reset without an interactive prompt.",
    ),
):
    """Reset a ledger by moving its prior contents to a timestamped backup."""
    if not yes:
        if not sys.stdin.isatty():
            emit(
                "confirmation_required",
                "Batch reset requires --yes in non-interactive mode.",
            )
            raise typer.Exit(2)
        if not typer.confirm(
            f"Reset {batch_state} and retain a backup?", default=False
        ):
            emit("cancelled", "Batch state was not reset.")
            raise typer.Exit(0)
    backup = reset_state(batch_state)
    if backup is None:
        emit(
            "batch_reset",
            "No batch state exists; nothing was reset.",
            state_path=str(batch_state),
        )
    else:
        emit(
            "batch_reset",
            f"Batch state reset; previous state retained at {backup}.",
            state_path=str(batch_state),
            backup_path=str(backup),
        )


PROVIDER_KEY_ENV = PROVIDER_KEY_NAMES


def _mask_secret(value: Optional[str]) -> str:
    """Return a non-reversible hint for a secret value."""
    if not value:
        return "(unset)"
    cleaned = value.strip()
    if len(cleaned) <= 8:
        return "set (••••)"
    return f"set ({cleaned[:4]}…{cleaned[-2:]})"


def _upsert_env_file(env_path: Path, key: str, value: str) -> None:
    """Add or replace a single KEY=value line, preserving other entries."""
    lines: list[str] = []
    replaced = False
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(f"{key}=") or line.strip().startswith(
                f"{key} ="
            ):
                lines.append(f"{key}={value}")
                replaced = True
            else:
                lines.append(line)
    if not replaced:
        lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@app.command("setup")
def setup() -> None:
    """Interactive first-run wizard: choose a provider, store a key, verify readiness."""
    if not sys.stdin.isatty():
        emit(
            "error",
            "Setup is interactive; run it in a terminal, or set the provider key "
            "environment variable and use `preflight` instead.",
        )
        raise typer.Exit(2)

    console.print(
        Panel(
            "[bold green]POCArchitect Setup[/bold green]\n"
            "This wizard stores a provider key in a local .env file and checks readiness.\n"
            "Your key is written only to .env in the current folder and is never printed.",
            expand=False,
        )
    )

    provider = (
        typer.prompt("Provider [xai/openai/groq/local]", default="xai").strip().lower()
    )
    while provider not in {"xai", "openai", "groq", "local"}:
        console.print("[red]Choose one of: xai, openai, groq, local[/red]")
        provider = typer.prompt("Provider", default="xai").strip().lower()

    if provider == "local":
        base_url = typer.prompt(
            "Local OpenAI-compatible endpoint", default=DEFAULT_LOCAL_BASE_URL
        ).strip()
        console.print(
            "Local providers need no API key. Verifying the endpoint is reachable…"
        )
        run_preflight(
            provider="local",
            base_url=base_url,
            require_api_key=True,
            output_format=output_format,
            no_color=no_color_state,
        )
    else:
        env_var = PROVIDER_KEY_ENV[provider]
        key = typer.prompt(f"Paste your {env_var}", hide_input=True).strip()
        if not key:
            emit("error", "No key entered; nothing was written.")
            raise typer.Exit(2)
        env_path = Path.cwd() / ".env"
        _upsert_env_file(env_path, env_var, key)
        emit(
            "setup_key_saved",
            f"Saved {env_var} to {env_path} (value not shown).",
            provider=provider,
        )
        console.print("Verifying provider readiness…")
        run_preflight(
            provider=provider,
            base_url=None,
            require_api_key=True,
            output_format=output_format,
            no_color=no_color_state,
        )

    if typer.confirm(
        "Run a safe dry-run now (no provider call, no report)?", default=True
    ):
        console.print(
            "\nRunning: [cyan]pocarchitect --url https://github.com/example/poc "
            "--no-ingest --dry-run[/cyan]\n"
        )
        try:
            process_single_url(
                url="https://github.com/example/poc",
                provider=provider,
                api_key=None,
                model=DEFAULT_MODELS.get(provider, "grok-3"),
                temperature=DEFAULT_TEMPERATURE,
                base_url=None,
                output_dir=get_default_output_dir(),
                risk_level=DEFAULT_RISK_LEVEL,
                target_os=DEFAULT_TARGET_OS,
                include_mitigations=True,
                no_ingest=True,
                dry_run=True,
                verbose=False,
                confirmed=True,
            )
        except typer.Exit:
            pass

    console.print(
        "\n[bold green]Setup complete.[/bold green] Next, try a real run, e.g.:\n"
        f"  [cyan]pocarchitect --url <owner/repo> --provider {provider}[/cyan]"
    )


@app.command("config")
def config_command() -> None:
    """Show effective settings and where each value comes from (keys masked)."""
    env_path = Path.cwd() / ".env"
    file_values = dotenv_values(env_path) if env_path.exists() else {}

    rows: list[dict[str, str]] = []

    def add(setting: str, value: str, source: str) -> None:
        rows.append({"setting": setting, "value": value, "source": source})

    for provider, env_var in PROVIDER_KEY_ENV.items():
        env_value = os.getenv(env_var)
        file_value = file_values.get(env_var)
        if env_value and (file_value is None or env_value != file_value):
            source = "environment"
        elif file_value and env_value == file_value:
            source = f".env ({env_path})"
        elif file_value:
            source = f".env ({env_path})"
        else:
            source = "unset"
        add(env_var, _mask_secret(env_value or file_value), source)

    add(
        "default output dir",
        str(get_default_output_dir()),
        (
            "IN_DOCKER"
            if (Path("/.dockerenv").exists() or os.getenv("IN_DOCKER"))
            else "cwd"
        ),
    )
    add("IN_DOCKER", os.getenv("IN_DOCKER") or "(unset)", "environment")
    for provider, model_name in DEFAULT_MODELS.items():
        add(f"default model ({provider})", model_name, "built-in default")

    if output_format == "json":
        emit(
            "config",
            "Effective configuration.",
            settings=rows,
            env_file=str(env_path) if env_path.exists() else None,
        )
        return

    table = Table(title="Effective Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Source", style="magenta")
    for row in rows:
        table.add_row(row["setting"], row["value"], row["source"])
    console.print(table)
    console.print(
        "Provider keys are masked. Real environment variables take precedence over .env."
    )


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    url: Optional[str] = typer.Option(
        None,
        "--url",
        "-u",
        help="Single PoC URL; public GitHub repositories can be grounded.",
    ),
    batch: Optional[Path] = typer.Option(
        None,
        "--batch",
        "-b",
        help="Text file; blank lines and full-line # comments are ignored.",
    ),
    provider: Literal["xai", "openai", "groq", "local"] = typer.Option(
        DEFAULT_PROVIDER, "--provider", "-p", help="LLM provider to use."
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="Model name (default: provider-specific)"
    ),
    temperature: float = typer.Option(
        DEFAULT_TEMPERATURE,
        "--temperature",
        "-t",
        help="Provider sampling temperature.",
    ),
    base_url: Optional[str] = typer.Option(
        None, "--base-url", help="OpenAI-compatible endpoint for --provider local."
    ),
    output_dir: Optional[Path] = typer.Option(
        None, "--output-dir", help="Directory where successful reports are written."
    ),
    risk_level: str = typer.Option(
        DEFAULT_RISK_LEVEL,
        "--risk-level",
        help="Free-text risk label sent to the provider.",
    ),
    target_os: str = typer.Option(
        DEFAULT_TARGET_OS,
        "--target-os",
        help="Free-text target environment sent to the provider.",
    ),
    include_mitigations: bool = typer.Option(
        True,
        "--include-mitigations/--no-mitigations",
        help="Include mitigation instructions in the report (use --no-mitigations to omit).",
    ),
    no_ingest: bool = typer.Option(
        False, "--no-ingest", help="Skip GitHub repository grounding."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show the prompt summary and exit without calling LLM"
    ),
    full: bool = typer.Option(
        False,
        "--full",
        help="With --dry-run, print the entire prompt instead of a summary.",
    ),
    open_report: bool = typer.Option(
        False,
        "--open",
        help="Open each finished report in your default viewer.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output (extra details during grounding)",
    ),
    batch_state: Optional[Path] = typer.Option(
        None,
        "--batch-state",
        help="JSON progress file used to resume completed batch URLs.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        help="Confirm source transfer without an interactive prompt.",
    ),
    output_format: Literal["text", "json"] = typer.Option(
        "text", "--format", help="Output mode: text or JSON Lines."
    ),
    no_color: bool = typer.Option(
        False, "--no-color", help="Disable ANSI color and style sequences."
    ),
    version: bool = typer.Option(
        False, "--version", "-V", help="Show version and exit"
    ),
):
    configure_output(output_format, no_color)
    if ctx.invoked_subcommand is not None:
        return

    if version:
        from . import __version__

        emit("version", f"POCArchitect v{__version__}", version=__version__)
        raise typer.Exit(0)

    if output_dir is None:
        output_dir = get_default_output_dir()

    # Dry runs bypass automatic preflight; use the explicit preflight command for checks.
    if not dry_run:
        run_preflight(
            provider=provider,
            base_url=base_url,
            require_api_key=True,
            output_dir=output_dir,
            output_format=output_format,
            no_color=no_color,
        )

    # (#9) Resolve provider-specific default model if not explicitly set
    if model is None:
        model = DEFAULT_MODELS.get(provider.lower(), "grok-3")
        if verbose:
            emit("model_selected", f"Using default model for {provider}: {model}")

    if url and batch:
        emit("error", "Provide either --url or --batch, not both")
        raise typer.Exit(2)

    # (#3) Only show a spinner in an interactive, human-readable session.
    show_spinner = output_format == "text" and not dry_run and console.is_terminal

    if url:
        # (#6/#7) Accept owner/repo shorthand and reject a malformed GitHub URL early.
        try:
            url = validate_poc_url(url, no_ingest)
        except ValueError as error:
            emit("error", f"Invalid PoC URL: {error}", url=url)
            raise typer.Exit(2)
        process_single_url(
            url=url,
            provider=provider,
            api_key=None,
            model=model,
            temperature=temperature,
            base_url=base_url,
            output_dir=output_dir,
            risk_level=risk_level,
            target_os=target_os,
            include_mitigations=include_mitigations,
            no_ingest=no_ingest,
            dry_run=dry_run,
            verbose=verbose,
            confirmed=yes,
            open_report=open_report,
            dry_run_full=full,
            show_spinner=show_spinner,
        )
    elif batch:
        process_batch_file(
            batch_path=batch,
            provider=provider,
            api_key=None,
            model=model,
            temperature=temperature,
            base_url=base_url,
            output_dir=output_dir,
            risk_level=risk_level,
            target_os=target_os,
            include_mitigations=include_mitigations,
            no_ingest=no_ingest,
            dry_run=dry_run,
            verbose=verbose,
            state_path=batch_state,
            confirmed=yes,
            open_report=open_report,
            dry_run_full=full,
        )
    else:
        emit("error", "Provide --url or --batch")
        raise typer.Exit(2)


if __name__ == "__main__":
    app()
