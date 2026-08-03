#!/usr/bin/env python3
import hashlib
import json
import os
import re
import subprocess
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
from .preflight import main as run_preflight

load_dotenv(override=False)

app = typer.Typer(
    name="pocarchitect",
    help="POCArchitect AI Agent - Turn messy PoCs into clean, reproducible blueprints.",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()

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
):
    """Run environment preflight checks"""
    run_preflight(require_api_key=not offline, offline=offline)


def load_prompt() -> str:
    try:
        prompt_file = files("pocarchitect") / "POC_Architect_Prompt.md"
        return prompt_file.read_text(encoding="utf-8")
    except Exception as e:
        console.print(f"[bold red]Prompt error:[/] {friendly_error_message(e)}")
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
    console.print(f"[green]Report saved:[/] {output_path.name}")
    return output_path


SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:api[_ -]?key|access[_ -]?token|secret)\s*[:=]\s*[^\s]+"),
    re.compile(r"(?i)\b(?:sk|xai|gsk)-[A-Za-z0-9_-]{12,}"),
)


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


def print_sensitive_input_warning(text: str) -> None:
    categories = detect_sensitive_input(text)
    if categories:
        console.print(
            "[bold yellow]Warning:[/] source content appears to contain "
            f"{', '.join(categories)}. Review the source and report destination "
            "before sending it to the selected provider; matched values are not "
            "printed by POCArchitect. Use --no-ingest for a local dry run."
        )


def friendly_error_message(error: Exception) -> str:
    if isinstance(error, subprocess.TimeoutExpired):
        return (
            "The operation timed out. Check network access or retry with --no-ingest."
        )
    if isinstance(error, FileNotFoundError):
        return "A required file or executable was not found. Check the working directory and rerun preflight --offline."
    if isinstance(error, subprocess.CalledProcessError):
        return "Git failed while ingesting the repository. Confirm the URL is public and valid, then retry."
    message = str(error).strip()
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
            console.print(f"[dim]Cloning {repo_name} (shallow)...[/dim]", end=" ")
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
            console.print("[green]done[/]")

            if verbose:
                console.print(f"[dim]Grounding: Analyzing {repo_name}[/]")

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
                            console.print(f"[dim]  Skipped large file: {file_path}[/]")
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
                console.print(
                    f"[dim]  Found {len(critical)} critical files (showing up to 25)[/]"
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
        context.append(f"WARNING: Ingestion failed ({e}).")
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
        client = OpenAI(api_key=api_key or "ollama", base_url=base_url, timeout=60.0)
    elif p in ["xai", "openai", "groq"]:
        base = None
        if p == "xai":
            base = "https://api.x.ai/v1"
        elif p == "groq":
            base = "https://api.groq.com/openai/v1"
        client = OpenAI(api_key=api_key, base_url=base, timeout=60.0)
    else:
        console.print(f"[bold red]Unsupported provider: {provider}[/]")
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
        console.print("[bold red]Error: LLM returned empty content[/]")
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
):
    console.print(f"[bold cyan]Processing:[/] {url}")

    system_prompt = load_prompt()
    grounding = (
        ""
        if no_ingest
        else build_grounding_context(url, no_ingest=no_ingest, verbose=verbose)
    )

    user_message = f"""PoC URL: {url}

{grounding}

Operator Preferences (respect these exactly):
- Risk Level: {risk_level}
- Target OS / Environment: {target_os}
- Include Mitigations: {"Yes" if include_mitigations else "No"}"""

    if dry_run:
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

    print_sensitive_input_warning(grounding)
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
):
    """Read URLs from a text file and process each one sequentially."""
    if not batch_path.exists():
        console.print(f"[bold red]Error:[/] Batch file not found: {batch_path}")
        raise typer.Exit(1)

    raw = batch_path.read_text(encoding="utf-8")
    urls = [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    if not urls:
        console.print(
            "[bold red]Error:[/] Batch file is empty or contains no valid URLs"
        )
        raise typer.Exit(1)

    console.print(
        f"[bold cyan]Batch mode:[/] {len(urls)} URL(s) from {batch_path.name}"
    )
    processed_count = 0
    success_count = 0
    failure_count = 0
    failed_urls = []
    state_path = state_path or output_dir / "batch_progress.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        state = {"version": 1, "items": {}}
    skipped_completed = 0

    def write_state() -> None:
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    for i, url in enumerate(urls, 1):
        if state.get("items", {}).get(url, {}).get("status") == "success":
            skipped_completed += 1
            console.print(f"[dim]Skipping completed URL {i}/{len(urls)}: {url}[/]")
            continue
        processed_count += 1
        console.print(f"\n[bold]── URL {i}/{len(urls)} ──[/]")
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
            )
            success_count += 1
            state.setdefault("items", {})[url] = {
                "status": "success",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            write_state()
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
            write_state()
            console.print(
                f"[bold red]Batch item failed:[/] {url} (exit code {e.exit_code})."
            )
            console.print("[yellow]Continuing to next URL...[/]")
        except Exception as e:
            failure_count += 1
            failed_urls.append(url)
            state.setdefault("items", {})[url] = {
                "status": "failed",
                "error": friendly_error_message(e),
            }
            write_state()
            console.print(
                f"[bold red]Batch item failed:[/] {url}: {friendly_error_message(e)}"
            )
            console.print("[yellow]Continuing to next URL...[/]")

    console.print(
        f"\n[bold green]Batch complete:[/] total={len(urls)} processed={processed_count} "
        f"success={success_count} failed={failure_count} skipped={len(urls) - processed_count} "
        f"resumed={skipped_completed} state={state_path}"
    )
    if dry_run and processed_count < len(urls):
        console.print("[yellow]Dry-run mode processed only the first URL by design.[/]")
    if failed_urls:
        console.print("[yellow]Failed URLs:[/]")
        for failed_url in failed_urls:
            console.print(f" - {failed_url}")
    if skipped_completed:
        console.print(
            f"[dim]Resumed batch: {skipped_completed} completed URL(s) skipped.[/]"
        )


# ── Main CLI entry point ─────────────────────────────────────────────
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
    version: bool = typer.Option(
        False, "--version", "-V", help="Show version and exit"
    ),
):
    if ctx.invoked_subcommand is not None:
        return

    if version:
        from . import __version__

        console.print(f"POCArchitect v{__version__}")
        raise typer.Exit(0)

    # (#10) Skip preflight in dry-run mode (dry-run does not need API keys)
    if not dry_run:
        run_preflight(require_api_key=True)

    # (#9) Resolve provider-specific default model if not explicitly set
    if model is None:
        model = DEFAULT_MODELS.get(provider.lower(), "grok-3")
        if verbose:
            console.print(f"[dim]Using default model for {provider}: {model}[/]")

    if output_dir is None:
        output_dir = get_default_output_dir()

    if url and batch:
        console.print("[bold red]Error:[/] Provide either --url or --batch, not both")
        raise typer.Exit(1)

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
        )
    else:
        console.print("[bold red]Error:[/] Provide --url or --batch")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
