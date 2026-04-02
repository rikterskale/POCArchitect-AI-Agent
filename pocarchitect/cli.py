#!/usr/bin/env python3
import typer
import os
import tempfile
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import git
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import print as rprint
from openai import OpenAI

# ── NEW: Preflight support ─────────────────────────────────────
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
    """Run full environment pre-flight checks (Python version, deps, API key, prompt file, etc.)."""
    run_preflight()


def load_prompt() -> str:
    prompt_path = Path(__file__).parent.parent / "POC_Architect_Prompt.md"
    if not prompt_path.exists():
        console.print("[bold red]Error: POC_Architect_Prompt.md not found![/]", style="bold red")
        raise typer.Exit(1)
    return prompt_path.read_text(encoding="utf-8")


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
    """Unified LLM call – now supports local servers."""
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
            model=model, temperature=temperature,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
        )
        return response.choices[0].message.content.strip()

    elif p == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(model=model, temperature=temperature, max_tokens=8192,
                                          system=system_prompt, messages=[{"role": "user", "content": user_message}])
        return response.content[0].text.strip()

    elif p == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model_obj = genai.GenerativeModel(model_name=model, system_instruction=system_prompt)
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
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Base URL for local OpenAI-compatible server (required for --provider local)"),
    model: str = typer.Option("grok-4", "--model", "-m", help="Model name to use"),
    output_dir: Path = typer.Option(Path.cwd() / "reports", "--output-dir", "-o", help="Output directory"),
    temperature: float = typer.Option(0.0, "--temperature", "-t", help="Temperature (0.0 recommended)"),

    risk_level: str = typer.Option("auto", "--risk-level", help="Force risk level", choices=["Critical","High","Medium","Low","auto"]),
    target_os: str = typer.Option("auto", "--target-os", help="Target OS", choices=["Windows","Linux","macOS","cross-platform","auto"]),
    include_mitigations: bool = typer.Option(True, "--include-mitigations", "--mitigations"),
    no_mitigations: bool = typer.Option(False, "--no-mitigations"),
    target_version: Optional[str] = typer.Option(None, "--target-version"),

    no_ingest: bool = typer.Option(False, "--no-ingest", help="Disable Python-side PoC ingestion"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    version: bool = typer.Option(False, "--version"),
) -> None:
    """Generate full offensive security blueprints from PoC URLs."""
    if version:
        import pocarchitect
        console.print(f"[bold]POCArchitect v{pocarchitect.__version__}[/]")
        raise typer.Exit()

    if ctx.invoked_subcommand == "preflight":
        return

    # === Original main logic (unchanged) ===
    if not url:
        console.print("[bold red]Error: --url is required[/]")
        raise typer.Exit(1)

    console.print(Panel.fit("[bold green]POCArchitect AI Agent[/] starting…", border_style="blue"))

    # ... (your existing main logic continues here exactly as before) ...


if __name__ == "__main__":
    app()
