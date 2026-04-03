#!/usr/bin/env python3
import typer
import os
import tempfile
from pathlib import Path
from typing import Literal, Optional
from dotenv import load_dotenv
import git
from rich.console import Console
from rich.panel import Panel
from openai import OpenAI
from importlib.resources import files
import re
from datetime import datetime

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


def save_report(content: str, url: str, output_dir: Path):
    """Save with timestamp for easy versioning."""
    slug = slugify(url.split('/')[-1] or "unknown-poc")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"POCAnalysis_{slug}_{timestamp}.md"
    output_path = output_dir / filename

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    console.print(f"[green]✅ Report saved to:[/] {output_path}")


def build_grounding_context(poc_url: str, no_ingest: bool = False) -> str:
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

            context.append(f"Repository: {repo_name}")
            context.append("Critical files and content:")

            critical = []
            for root, dirs, files_list in os.walk(repo_path):
                if ".git" in dirs:
                    dirs.remove(".git")
                rel_root = Path(root).relative_to(repo_path)
                for file in files_list:
                    file_path = rel_root / file
                    full_path = Path(root) / file

                    if full_path.stat().st_size > 250_000:
                        continue

                    if any(k in file_path.name.lower() for k in ["readme", "exploit", "payload", "shell", "poc", "index", "attack"]):
                        try:
                            content = full_path.read_text(encoding="utf-8", errors="ignore")
                            if len(content) > 7500:
                                content = content[:7500] + "\n... [truncated]"
                            critical.append((str(file_path), content))
                        except Exception:
                            pass

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

    if p == "local":
        client = OpenAI(api_key=api_key or "ollama", base_url=base_url)
    elif p in ["xai", "openai", "groq"]:
        base = None
        if p == "xai": base = "https://api.x.ai/v1"
        elif p == "groq": base = "https://api.groq.com/openai/v1"
        client = OpenAI(api_key=api_key, base_url=base)
    else:
        console.print(f"[bold red]Unsupported provider: {provider}[/]")
        raise typer.Exit(1)

    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    )
    return response.choices[0].message.content.strip()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    url: Optional[str] = typer.Option(None, "--url", "-u", help="Single PoC URL"),
    provider: str = typer.Option("xai", "--provider", "-p"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k"),
    base_url: Optional[str] = typer.Option(None, "--base-url"),
    model: str = typer.Option(None, "--model", "-m"),
    output_dir: Path = typer.Option(Path.cwd() / "reports", "--output-dir", "-o"),
    temperature: float = typer.Option(0.0, "--temperature", "-t"),
    risk_level: Literal["Critical", "High", "Medium", "Low", "auto"] = typer.Option("auto", "--risk-level"),
    target_os: Literal["Windows", "Linux", "macOS", "cross-platform", "auto"] = typer.Option("auto", "--target-os"),
    include_mitigations: bool = typer.Option(True, "--include-mitigations", "--mitigations"),
    no_mitigations: bool = typer.Option(False, "--no-mitigations"),
    no_ingest: bool = typer.Option(False, "--no-ingest", help="Skip GitHub ingestion for very large repos"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    version: bool = typer.Option(False, "--version"),
):
    if ctx.invoked_subcommand is not None:
        return

    if version:
        from . import __version__
        console.print(f"[bold green]POCArchitect v{__version__}[/]")
        raise typer.Exit(0)

    if url is None:
        console.print("[bold red]Error: Missing option '--url' / '-u'.[/]")
        raise typer.Exit(1)

    if no_mitigations:
        include_mitigations = False

    # Auto-select good default model
    if model is None:
        if provider.lower() == "openai":
            model = "gpt-4o"
        elif provider.lower() == "xai":
            model = "grok-4"
        else:
            model = "gpt-4o-mini"

    console.print("[bold cyan]POCArchitect AI Agent[/] — Starting...")

    if not dry_run:
        try:
            run_preflight(silent=True)
        except Exception:
            pass

    system_prompt = load_prompt()
    grounding = "" if no_ingest else build_grounding_context(url)

    user_message = f"PoC URL: {url}\n\n{grounding}\n\nMANDATORY: Base your entire report on the grounding context above. Quote real code, file names, and techniques from the provided files. Do not hallucinate or use general knowledge when specific content is available."

    if dry_run:
        console.print(Panel(system_prompt + "\n\n" + user_message, title="Dry-run — Full Prompt", border_style="yellow"))
        raise typer.Exit(0)

    try:
        result = get_llm_response(
            provider=provider,
            api_key=api_key,
            model=model,
            temperature=temperature,
            base_url=base_url,
            system_prompt=system_prompt,
            user_message=user_message,
        )

        console.print(Panel(result, title="POC Architect Output", border_style="green"))
        save_report(result, url, output_dir)

    except Exception as e:
        console.print(f"[bold red]LLM Error: {e}[/]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()