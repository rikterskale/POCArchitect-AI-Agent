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
    """Run full environment pre-flight checks."""
    run_preflight()


def load_prompt() -> str:
    """Load the core system prompt from package data.
    
    This version works reliably whether running from source,
    after `pip install -e .`, or when installed from PyPI.
    """
    try:
        prompt_file = files("pocarchitect") / "POC_Architect_Prompt.md"
        return prompt_file.read_text(encoding="utf-8")
    except Exception as e:
        console.print(f"[bold red]Error: Could not load POC_Architect_Prompt.md from package: {e}[/]")
        console.print("[yellow]Make sure the prompt file is inside the 'pocarchitect/' package directory.[/]")
        raise typer.Exit(1)


def build_grounding_context(poc_url: str) -> str:
    """Auto-fetch repo files and build concise grounding context (zero hallucinations)."""
    context = ["=== GROUNDING CONTEXT (auto-fetched by POCArchitect CLI) ==="]
    context.append(f"PoC URL: {poc_url}\n")

    if not poc_url.startswith("https://github.com/"):
        context.append("NOTE: Non-GitHub URL. No automatic cloning performed.")
        return "\n".join(context)

    try:
        parts = poc_url.rstrip("/").split("/")
        if len(parts) < 5 or "github.com" not in parts[2]:
            context.append("ERROR: Could not parse GitHub repo URL.")
            return "\n".join(context)

        repo_name = f"{parts[3]}/{parts[4]}"
        clone_url = poc_url if poc_url.endswith(".git") else poc_url + ".git"

        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_path = Path(tmp_dir) / "poc"
            console.print(f"[dim]Cloning {repo_name} (shallow)...[/dim]", end=" ")
            git.Repo.clone_from(clone_url, repo_path, depth=1, single_branch=True)
            console.print("[green]done[/]")

            context.append(f"Repository: {repo_name}")
            context.append("File tree:")
            files_found = []
            critical_files = []

            for root, dirs, files in os.walk(repo_path):
                if ".git" in dirs:
                    dirs.remove(".git")
                rel_root = Path(root).relative_to(repo_path)
                for file in files:
                    file_path = rel_root / file
                    full_path = Path(root) / file
                    files_found.append(str(file_path))

                    if (file_path.name in {"README.md", "Dockerfile"} or
                        file_path.suffix in {".py", ".js", ".go", ".c", ".cpp", ".sh", ".md", ".txt"} or
                        any(x in file_path.name.lower() for x in ["exploit", "poc", "payload"])) and full_path.stat().st_size < 150_000:

                        try:
                            content = full_path.read_text(encoding="utf-8", errors="ignore")
                            if len(content) > 8000:
                                content = content[:8000] + "\n... [truncated]"
                            critical_files.append((str(file_path), content))
                        except Exception:
                            pass

            context.append("\n".join(f"├── {f}" for f in files_found[:30]))
            context.append("\nCRITICAL FILES CONTENT:")
            for filepath, content in critical_files[:12]:
                lang = Path(filepath).suffix[1:] if Path(filepath).suffix else "text"
                context.append(f"\nFile: {filepath}")
                context.append(f"```{lang}")
                context.append(content.strip())
                context.append("```")
            context.append("\nEnd of grounding context.")
            return "\n".join(context)

    except Exception as e:
        context.append(f"WARNING: Ingestion failed ({e}). Falling back to URL-only mode.")
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
    """Unified LLM call – supports xAI, OpenAI, Groq, Anthropic, Gemini, and local servers."""
    p = provider.lower()

    if p == "local":
        client = OpenAI(api_key=api_key or "ollama", base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content.strip()

    elif p in ["xai", "openai", "groq"]:
        base = None
        if p == "xai":
            base = "https://api.x.ai/v1"
        elif p == "groq":
            base = "https://api.groq.com/openai/v1"
        client = OpenAI(api_key=api_key, base_url=base)
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
        )
        return response.choices[0].message.content.strip()

    elif p == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            temperature=temperature,
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        return response.content[0].text.strip()

    elif p == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model_obj = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_prompt
        )
        response = model_obj.generate_content(user_message)
        return response.text.strip()

    else:
        console.print(f"[bold red]Error: Unsupported provider: {provider}[/]", style="bold red")
        raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    url: str = typer.Option(..., "--url", "-u", help="Single PoC URL or path to batch file"),
    provider: str = typer.Option("xai", "--provider", "-p",
                                 help="LLM provider: xai, openai, groq, anthropic, gemini, local"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="API key (auto-loaded from .env)"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Base URL for local OpenAI-compatible server"),
    model: str = typer.Option("grok-4", "--model", "-m", help="Model name to use"),
    output_dir: Path = typer.Option(Path.cwd() / "reports", "--output-dir", "-o", help="Output directory"),
    temperature: float = typer.Option(0.0, "--temperature", "-t", help="Temperature (0.0 recommended)"),

    risk_level: str = typer.Option("auto", "--risk-level", help="Force risk level", 
                                   choices=["Critical", "High", "Medium", "Low", "auto"]),
    target_os: str = typer.Option("auto", "--target-os", help="Target OS", 
                                  choices=["Windows", "Linux", "macOS", "cross-platform", "auto"]),
    include_mitigations: bool = typer.Option(True, "--include-mitigations", "--mitigations"),
    no_mitigations: bool = typer.Option(False, "--no-mitigations"),
    target_version: Optional[str] = typer.Option(None, "--target-version"),

    no_ingest: bool = typer.Option(False, "--no-ingest", help="Disable Python-side PoC ingestion"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    version: bool = typer.Option(False, "--version", "-V", help="Show version and exit"),
):
    """Main entrypoint for POCArchitect."""
    if version:
        console.print("[bold]POCArchitect AI Agent[/] v0.2.0")
        raise typer.Exit()

    if ctx.invoked_subcommand is not None:
        return

    # Load system prompt (now production-safe)
    system_prompt = load_prompt()

    # Build user message + grounding
    if no_ingest:
        user_message = f"Analyze this PoC and generate a full operational blueprint:\n\nURL: {url}"
    else:
        grounding = build_grounding_context(url)
        user_message = f"{grounding}\n\nGenerate a complete, production-ready operational blueprint for the above PoC."

    if dry_run:
        console.print(Panel("[yellow]DRY RUN MODE - No LLM call will be made[/]", title="Dry Run"))
        console.print(f"[dim]Would send to {provider} using model {model}[/]")
        return

    console.print(f"[bold]Generating blueprint for:[/] {url}")
    console.print(f"[dim]Provider:[/] {provider} • [dim]Model:[/] {model}")

    try:
        response = get_llm_response(
            provider=provider,
            api_key=api_key,
            model=model,
            temperature=temperature,
            base_url=base_url,
            system_prompt=system_prompt,
            user_message=user_message,
        )

        # Save report
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(url).name.replace("/", "_").replace(":", "_").replace("?", "_")
        report_path = output_dir / f"poc_blueprint_{safe_name}.md"
        report_path.write_text(response, encoding="utf-8")

        console.print(Panel.fit(
            f"[green]Blueprint generated successfully![/]\nSaved to: [bold]{report_path}[/]",
            border_style="green"
        ))

    except Exception as e:
        console.print(f"[bold red]Error during LLM call: {e}[/]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
