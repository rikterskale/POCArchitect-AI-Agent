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

load_dotenv(override=False)

app = typer.Typer(
    name="pocarchitect",
    help="POCArchitect AI Agent - Turn messy PoCs into clean, reproducible blueprints.",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()


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
        # Local servers usually don't need a real key
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

    # Existing providers (xai, openai, groq, anthropic, gemini) – unchanged
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
):
    """Generate full offensive security blueprints from PoC URLs."""

    # Resolve API key
    if api_key is None and provider.lower() != "local":
        p = provider.lower()
        key_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
        }
        api_key = os.getenv(key_map.get(p, f"{p.upper()}_API_KEY")) or os.getenv("OPENAI_API_KEY")
        if not api_key:
            console.print(f"[bold red]No API key for {provider}. Set in .env or use --api-key[/]", style="bold red")
            raise typer.Exit(1)

    if no_mitigations:
        include_mitigations = False

    if version:
        try:
            from pocarchitect import __version__
            console.print(f"[bold cyan]POCArchitect[/bold cyan] v{__version__}")
        except ImportError:
            console.print("[bold cyan]POCArchitect[/bold cyan] (version unknown)")
        raise typer.Exit()

    console.print(Panel.fit("[bold green]POCArchitect AI Agent[/] — Forging blueprints of digital domination", border_style="green"))

    prompt = load_prompt()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Batch handling
    urls: list[str] = []
    input_path = Path(url)
    if input_path.exists() and input_path.suffix in (".txt", ""):
        content = input_path.read_text(encoding="utf-8")
        urls = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]
        console.print(f"[cyan]Batch mode — {len(urls)} URLs loaded[/]")
    else:
        urls = [url]

    if dry_run:
        console.print("[bold yellow]DRY-RUN MODE ENABLED[/]")
        raise typer.Exit()

    with Progress(SpinnerColumn(), TextColumn("[bold cyan]{task.description}"), console=console) as progress:
        task = progress.add_task("Processing PoCs...", total=len(urls))
        for i, poc_url in enumerate(urls, 1):
            progress.update(task, description=f"Processing {i}/{len(urls)} → [yellow]{poc_url[:70]}...[/]")

            grounding = "NOTE: --no-ingest used." if no_ingest else build_grounding_context(poc_url)

            user_message = f"""Analyze this Proof-of-Concept and generate the COMPLETE offensive security blueprint.

{grounding}

Risk Level Preference: {risk_level}
Target OS: {target_os}
Include Mitigations: {include_mitigations}
Target Version: {target_version or 'Not specified'}

Follow the exact 7-phase pipeline in the system prompt.
Apply the operator preferences above.
Output ONLY the Markdown blueprint (no extra text)."""

            try:
                if verbose:
                    console.print(f"[dim]Calling {provider} with model: {model}[/]")

                blueprint = get_llm_response(
                    provider=provider,
                    api_key=api_key,
                    model=model,
                    temperature=temperature,
                    base_url=base_url,
                    system_prompt=prompt,
                    user_message=user_message,
                )

                safe_name = poc_url.split("/")[-1].replace(".git", "").replace("/", "_")[:100]
                output_path = output_dir / f"POC_Blueprint_{safe_name}.md"
                output_path.write_text(blueprint, encoding="utf-8")
                rprint(f"[bold green]Saved:[/] [cyan]{output_path.name}[/]")

            except Exception as e:
                console.print(f"[bold red]Error processing {poc_url}: {e}[/]")
                if verbose:
                    import traceback
                    console.print(traceback.format_exc())

    console.print(Panel.fit(f"[bold green]✅ All done! {len(urls)} blueprint(s) saved to {output_dir}[/]", border_style="green"))


if __name__ == "__main__":
    app()
