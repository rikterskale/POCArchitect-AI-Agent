#!/usr/bin/env python3
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import urlparse

import typer
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# ── Preflight support ─────────────────────────────────────
from .output import event_payload
from .preflight import DEFAULT_LOCAL_BASE_URL, main as run_preflight
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
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()
output_format = "text"


def configure_output(format_name: str, no_color: bool) -> None:
    """Configure the shared presentation layer before any command emits output."""
    global console, output_format
    output_format = format_name
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


# ── Provider-specific default models (#9) ─────────────────
DEFAULT_MODELS = {
    "xai": "grok-3",
    "openai": "gpt-4o",
    "groq": "llama-3.1-70b-versatile",
    "local": "qwen2.5-coder:32b",
}


@app.command("preflight")
def preflight(
    offline: bool = typer.Option(
        False,
        "--offline",
        help="Check installation without requiring an API key or provider access.",
    ),
    provider: Literal["xai", "openai", "groq", "local"] = typer.Option(
        "xai", "--provider", "-p", help="Provider whose readiness to check."
    ),
    base_url: Optional[str] = typer.Option(
        None, "--base-url", help="OpenAI-compatible local provider endpoint."
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
        output_format=output_format,
        no_color=no_color,
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
    if Path("/.dockerenv").exists() or os.getenv("IN_DOCKER"):
        return Path("/reports")
    return Path.cwd() / "reports"


def save_report(
    content: str,
    url: str,
    output_dir: Path,
    provider: str,
    model: str,
    no_ingest: bool,
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
        "ingestion": "disabled" if no_ingest else "github-shallow-clone",
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }
    metadata_block = (
        "---\n"
        + "\n".join(f"{key}: {json.dumps(value)}" for key, value in metadata.items())
        + "\n---\n\n"
    )
    output_path.write_text(metadata_block + content, encoding="utf-8")
    emit("report_saved", f"Report saved: {output_path.name}", path=str(output_path))
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
    emit(
        "ingestion_preview",
        "Ingestion preview: source will be sent to the selected provider after redaction.",
        provider=provider,
        model=model,
        classification=classification,
        redaction_count=redaction_count,
        character_count=len(redacted),
        estimated_tokens=max(1, len(redacted) // 4),
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
    if "401" in message or "unauthorized" in message.lower():
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
) -> str:
    if no_ingest:
        return f"PoC URL: {poc_url}\n[Grounding disabled by --no-ingest]"

    context = ["=== GROUNDING CONTEXT — USE THIS HEAVILY ==="]
    context.append(f"PoC URL: {poc_url}\n")

    parsed = urlparse(poc_url.strip())
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        context.append("Non-GitHub URL — limited analysis.")
        return "\n".join(context)

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
                        except Exception:
                            pass

            if verbose:
                emit(
                    "grounding",
                    f"Found {len(critical)} critical files (showing up to 25).",
                )

            for filepath, content in critical[:25]:
                lang = Path(filepath).suffix[1:] if Path(filepath).suffix else "text"
                context.append(f"\n--- File: {filepath} ---")
                context.append(f"```{lang}")
                context.append(content.strip())
                context.append("```")

            context.append("\n=== END OF GROUNDING CONTEXT ===\n")
            context.append(
                "MANDATORY: Base your entire report on the files above. Quote real code and techniques. Do not hallucinate."
            )
            return "\n".join(context)

    except Exception as e:
        context.append(f"WARNING: Ingestion failed ({friendly_error_message(e)}).")
        return "\n".join(context)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((Exception,)),
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
        env_map = {
            "xai": "XAI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "groq": "GROQ_API_KEY",
        }
        env_var = env_map.get(p)
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

    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

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
):
    emit("processing", f"Processing: {url}", url=url)

    system_prompt = load_prompt()
    grounding = (
        ""
        if no_ingest
        else build_grounding_context(url, no_ingest=no_ingest, verbose=verbose)
    )
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
        full_prompt = f"--- SYSTEM PROMPT ---\n{system_prompt}\n\n--- USER MESSAGE ---\n{user_message}"
        console.print(
            Panel(
                full_prompt,
                title="Full Prompt (Ready for LLM)",
                border_style="blue",
                expand=True,
            )
        )
        raise typer.Exit(0)

    result = get_llm_response(
        provider=provider,
        api_key=api_key,
        model=model,
        temperature=temperature,
        base_url=base_url,
        system_prompt=system_prompt,
        user_message=user_message,
    )

    return save_report(result, url, output_dir, provider, model, no_ingest)


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

    for i, url in enumerate(urls, 1):
        if state.get("items", {}).get(url, {}).get("status") == "success":
            skipped_completed += 1
            emit(
                "batch_skipped",
                f"Skipping completed URL {i}/{len(urls)}: {url}",
                url=url,
            )
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
                break  # dry-run exits after first URL
            failure_count += 1
            failed_urls.append(url)
            state.setdefault("items", {})[url] = {
                "status": "failed",
                "error": f"exit code {e.exit_code}",
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
            }
            persist_state()
            emit(
                "batch_item_failed",
                f"Batch item failed: {url}: {friendly_error_message(e)}",
                url=url,
            )
            emit("batch_continue", "Continuing to next URL...")

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
    if dry_run and processed_count < len(urls):
        emit("batch_dry_run", "Dry-run mode processed only the first URL by design.")
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


# ── Main CLI entry point ─────────────────────────────────────────────
@app.command("batch-status")
def batch_status(
    batch_state: Path = typer.Option(
        Path("reports/batch_progress.json"),
        "--batch-state",
        help="Batch ledger to inspect.",
    ),
):
    """Show a concise, machine-readable summary of batch recovery state."""
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


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    url: Optional[str] = typer.Option(
        None, "--url", "-u", help="Single PoC GitHub URL"
    ),
    batch: Optional[Path] = typer.Option(
        None, "--batch", "-b", help="Path to .txt file with multiple URLs"
    ),
    provider: Literal["xai", "openai", "groq", "local"] = typer.Option(
        "xai", "--provider", "-p"
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="Model name (default: provider-specific)"
    ),
    temperature: float = typer.Option(0.2, "--temperature", "-t"),
    base_url: Optional[str] = typer.Option(None, "--base-url"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir"),
    risk_level: str = typer.Option("High", "--risk-level"),
    target_os: str = typer.Option("Linux", "--target-os"),
    include_mitigations: bool = typer.Option(True, "--include-mitigations"),
    no_ingest: bool = typer.Option(False, "--no-ingest"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show full prompt and exit without calling LLM"
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

    # (#10) Skip preflight in dry-run mode (dry-run does not need API keys)
    if not dry_run:
        run_preflight(
            provider=provider,
            base_url=base_url,
            require_api_key=True,
            output_format=output_format,
            no_color=no_color,
        )

    # (#9) Resolve provider-specific default model if not explicitly set
    if model is None:
        model = DEFAULT_MODELS.get(provider.lower(), "grok-3")
        if verbose:
            emit("model_selected", f"Using default model for {provider}: {model}")

    if output_dir is None:
        output_dir = get_default_output_dir()

    if url and batch:
        emit("error", "Provide either --url or --batch, not both")
        raise typer.Exit(2)

    if url:
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
        )
    else:
        emit("error", "Provide --url or --batch")
        raise typer.Exit(2)


if __name__ == "__main__":
    app()
