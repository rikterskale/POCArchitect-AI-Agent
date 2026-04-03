#!/usr/bin/env python3
import typer
import os
import tempfile
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import git
from rich.console import Console
from rich.panel import Panel
from openai import OpenAI
from importlib.resources import files
import re
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

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


@app.command("preflight")
def preflight():
    """Run environment preflight checks"""
    run_preflight()


def load_prompt() -> str:
    try:
        prompt_file = files("pocarchitect") / "POC_Architect_Prompt.md"
        return prompt_file.read_text(encoding="utf-8")
    except Exception as e:
        console.print(f"[bold red]Error loading prompt: {e}[/]")
        raise typer.Exit(1)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text[:60]


def get_default_output_dir() -> Path:
    if Path("/.dockerenv").exists() or os.getenv("IN_DOCKER"):
        return Path("/reports")
    return Path.cwd() / "reports"


def save_report(content: str, url: str, output_dir: Path) -> Path:
    slug = slugify(url.split('/')[-1] or "unknown-poc")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"POCAnalysis_{slug}_{timestamp}.md"
    output_path = output_dir / filename

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    console.print(f"[green]Report saved:[/] {output_path.name}")
    return output_path


def build_grounding_context(poc_url: str, no_ingest: bool = False, verbose: bool = False) -> str:
    if no_ingest:
        return f"PoC URL: {poc_url}\n[Grounding disabled by --no-ingest]"

    context = ["=== GROUNDING CONTEXT — USE THIS HEAVILY ==="]
    context.append(f"PoC URL: {poc_url}\n")

    if not poc_url.startswith("https://github.com/"):
        context.append("Non-GitHub URL — limited analysis.")
        return "\n".join(context)

    try:
        parts = poc_url.rstrip("/").split("/")
        repo_name = f"{parts[3]}/{parts[4]}"
        clone_url = poc_url if poc_url.endswith(".git") else poc_url + ".git"

        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_path = Path(tmp_dir) / "poc"
            console.print(f"[dim]Cloning {repo_name} (shallow)...[/dim]", end=" ")
            git.Repo.clone_from(clone_url, repo_path, depth=1, single_branch=True)
            console.print("[green]done[/]")

            if verbose:
                console.print(f"[dim]Grounding: Analyzing {repo_name}[/]")

            context.append(f"Repository: {repo_name}")
            context.append("Critical files and content:")

            critical = []
            keywords = ["readme", "exploit", "payload", "shell", "poc", "index", "attack",
                        "main", "vuln", "trigger", "scan", "app", "setup", "install",
                        "dockerfile", "makefile", "requirements", "config", "manifest"]
            extensions = {".py", ".sh", ".ps1", ".yml", ".yaml", ".json", ".md",
                         ".txt", ".bat", ".cmd", ".cpp", ".c", ".go", ".rs"}

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
                    if (any(k in lower_name for k in keywords) or
                        Path(file_path).suffix.lower() in extensions):
                        try:
                            content = full_path.read_text(encoding="utf-8", errors="ignore")
                            if len(content) > 7500:
                                content = content[:7500] + "\n... [truncated]"
                            critical.append((str(file_path), content))
                        except Exception:
                            pass

            if verbose:
                console.print(f"[dim]  Found {len(critical)} critical files (showing up to 25)[/]")

            for filepath, content in critical[:25]:
                lang = Path(filepath).suffix[1:] if Path(filepath).suffix else "text"
                context.append(f"\n--- File: {filepath} ---")
                context.append(f"```{lang}")
                context.append(content.strip())
                context.append("```")

            context.append("\n=== END OF GROUNDING CONTEXT ===\n")
            context.append("MANDATORY: Base your entire report on the files above. Quote real code and techniques. Do not hallucinate.")
            return "\n".join(context)

    except Exception as e:
        context.append(f"WARNING: Ingestion failed ({e}).")
        return "\n".join(context)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((Exception,)),
    reraise=True
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
    if api_key is None:
        env_map = {
            "xai": "XAI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "groq": "GROQ_API_KEY",
        }
        api_key = os.getenv(env_map.get(provider.lower()))

    p = provider.lower()

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
            {"role": "user", "content": user_message}
        ],
        timeout=60.0
    )
    return response.choices[0].message.content.strip()


def process_single_url(url: str, provider: str, api_key: Optional[str], model: str,
                       temperature: float, base_url: Optional[str], output_dir: Path,
                       risk_level: str, target_os: str, include_mitigations: bool,
                       no_ingest: bool, dry_run: bool = False, verbose: bool = False):
    console.print(f"[bold cyan]Processing:[/] {url}")

    system_prompt = load_prompt()
    grounding = "" if no_ingest else build_grounding_context(url, no_ingest=no_ingest, verbose=verbose)

    user_message = f"""PoC URL: {url}

{grounding}

Operator Preferences (respect these exactly):
- Risk Level: {risk_level}
- Target OS / Environment: {target_os}
- Include Mitigations: {'Yes' if include_mitigations else 'No'}"""

    if dry_run:
        console.print("[bold green]🚀 DRY RUN MODE — No LLM call will be made[/bold green]")
        full_prompt = f"--- SYSTEM PROMPT ---\n{system_prompt}\n\n--- USER MESSAGE ---\n{user_message}"
        console.print(Panel(full_prompt, title="Full Prompt (Ready for LLM)", border_style="blue", expand=True))
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

    save_report(result, url, output_dir)


# ── Main CLI entry point ─────────────────────────────────────────────
@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    url: Optional[str] = typer.Option(None, "--url", "-u", help="Single PoC GitHub URL"),
    batch: Optional[Path] = typer.Option(None, "--batch", "-b", help="Path to .txt file with multiple URLs"),
    provider: str = typer.Option("xai", "--provider", "-p"),
    model: str = typer.Option("grok-3", "--model", "-m"),
    temperature: float = typer.Option(0.2, "--temperature", "-t"),
    base_url: Optional[str] = typer.Option(None, "--base-url"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir"),
    risk_level: str = typer.Option("High", "--risk-level"),
    target_os: str = typer.Option("Linux", "--target-os"),
    include_mitigations: bool = typer.Option(True, "--include-mitigations"),
    no_ingest: bool = typer.Option(False, "--no-ingest"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show full prompt and exit without calling LLM"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output (extra details during grounding)"),
    version: bool = typer.Option(False, "--version", "-V", help="Show version and exit"),
):
    if ctx.invoked_subcommand is not None:
        return

    if version:
        from . import __version__
        console.print(f"POCArchitect v{__version__}")
        raise typer.Exit(0)

    run_preflight()

    if output_dir is None:
        output_dir = get_default_output_dir()

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
        console.print("[yellow]Batch mode coming in next update...[/]")
    else:
        console.print("[bold red]Error:[/] Provide --url or --batch")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()