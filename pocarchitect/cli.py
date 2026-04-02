#!/usr/bin/env python3
import typer
import os
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import print as rprint
from openai import OpenAI
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv  # auto-load .env

# Load .env automatically (before Typer parses anything)
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
    """Load the system prompt from the project root."""
    prompt_path = Path(__file__).parent.parent / "POC_Architect_Prompt.md"
    if not prompt_path.exists():
        console.print("[bold red]Error: POC_Architect_Prompt.md not found![/]", style="bold red")
        raise typer.Exit(1)
    return prompt_path.read_text(encoding="utf-8")


def get_llm_response(
    provider: str,
    api_key: str,
    model: str,
    temperature: float,
    system_prompt: str,
    user_message: str,
) -> str:
    """Unified LLM call for all supported providers."""
    p = provider.lower()

    # ==================== OpenAI-compatible providers ====================
    if p in ["xai", "openai", "groq"]:
        base_url = None
        if p == "xai":
            base_url = "https://api.x.ai/v1"
        elif p == "groq":
            base_url = "https://api.groq.com/openai/v1"

        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content.strip()

    # ==================== Anthropic ====================
    elif p == "anthropic":
        try:
            import anthropic
        except ImportError:
            console.print(
                "[bold red]Error: Anthropic support requires the 'anthropic' package.[/]\n"
                "Run: [yellow]pip install anthropic[/]",
                style="bold red",
            )
            raise typer.Exit(1)

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            temperature=temperature,
            max_tokens=8192,  # generous default for Claude
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text.strip()

    # ==================== Gemini ====================
    elif p == "gemini":
        try:
            import google.generativeai as genai
        except ImportError:
            console.print(
                "[bold red]Error: Gemini support requires the 'google-generativeai' package.[/]\n"
                "Run: [yellow]pip install google-generativeai[/]",
                style="bold red",
            )
            raise typer.Exit(1)

        genai.configure(api_key=api_key)
        model_obj = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_prompt,
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

    # Core flags
    provider: str = typer.Option(
        "xai",
        "--provider",
        "-p",
        help="LLM provider: xai, openai, groq, anthropic, gemini",
        case_sensitive=False,
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key (auto-loaded from .env using provider-specific keys)",
    ),
    model: str = typer.Option("grok-4", "--model", "-m", help="Model name to use"),
    output_dir: Path = typer.Option(
        Path.cwd() / "reports", "--output-dir", "-o", help="Output directory"
    ),
    temperature: float = typer.Option(0.0, "--temperature", "-t", help="Temperature (0.0 recommended)"),

    # Operator control flags
    risk_level: str = typer.Option(
        "auto",
        "--risk-level",
        help="Force risk level in the report",
        choices=["Critical", "High", "Medium", "Low", "auto"],
    ),
    target_os: str = typer.Option(
        "auto",
        "--target-os",
        help="Target operating system for instructions",
        choices=["Windows", "Linux", "macOS", "cross-platform", "auto"],
    ),
    include_mitigations: bool = typer.Option(
        True,
        "--include-mitigations",
        "--mitigations",
        help="Include mitigation recommendations (default: True)",
    ),
    no_mitigations: bool = typer.Option(
        False,
        "--no-mitigations",
        help="Disable mitigation recommendations",
    ),
    target_version: Optional[str] = typer.Option(
        None,
        "--target-version",
        help="Specific vulnerable software version (e.g. 1.2.3)",
    ),

    # Extra flags
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show final prompt and exit without calling LLM"),
    version: bool = typer.Option(False, "--version", help="Show version and exit"),
):
    """Generate full offensive security blueprints from PoC URLs."""

    # Resolve API key from .env if not passed on command line
    if api_key is None:
        p = provider.lower()
        if p == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
        elif p == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
        elif p == "groq":
            api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
        else:
            api_key = os.getenv("XAI_API_KEY") or os.getenv("OPENAI_API_KEY")

        if not api_key:
            console.print(
                f"[bold red]Error: No API key found for provider '{provider}'.[/]\n"
                f"Set it in .env as {p.upper()}_API_KEY or pass --api-key",
                style="bold red",
            )
            raise typer.Exit(1)

    # Handle --no-mitigations
    if no_mitigations:
        include_mitigations = False

    if version:
        try:
            from pocarchitect import __version__
            console.print(f"[bold cyan]POCArchitect[/bold cyan] v{__version__}")
        except ImportError:
            console.print("[bold cyan]POCArchitect[/bold cyan] (version unknown)")
        raise typer.Exit()

    # Show help if no arguments
    if not ctx.args and url == typer.Option(..., "--url", "-u").default:
        typer.echo(ctx.get_help())
        raise typer.Exit()

    console.print(
        Panel.fit(
            "[bold green]POCArchitect AI Agent[/] — Forging blueprints of digital domination",
            border_style="green"
        )
    )

    prompt = load_prompt()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect operator options
    operator_options = {
        "risk_level": risk_level,
        "target_os": target_os,
        "include_mitigations": include_mitigations,
        "target_version": target_version,
    }

    # Batch or single mode
    urls: list[str] = []
    input_path = Path(url)
    if input_path.exists() and (input_path.suffix in (".txt", "") or input_path.is_dir()):
        content = input_path.read_text(encoding="utf-8")
        urls = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]
        console.print(f"[cyan]Batch mode — {len(urls)} URLs loaded[/]")
    else:
        urls = [url]

    # ==================== DRY-RUN MODE ====================
    if dry_run:
        console.print("[bold yellow]DRY-RUN MODE ENABLED[/]")
        for i, poc_url in enumerate(urls, 1):
            console.print(f"\n[bold cyan]--- Dry Run {i}/{len(urls)} ---[/]")
            console.print(f"URL: {poc_url}")
            user_message = f"""Analyze this Proof-of-Concept and generate the COMPLETE offensive security blueprint.

PoC URL: {poc_url}
Risk Level Preference: {risk_level}
Target OS: {target_os}
Include Mitigations: {include_mitigations}
Target Version: {target_version or 'Not specified'}

Follow the exact 7-phase pipeline in the system prompt. 
Apply the operator preferences above when generating the report.
Output ONLY the Markdown blueprint (no extra text)."""

            console.print(Panel(
                f"[bold]System Prompt (first 500 chars):[/]\n{prompt[:500]}...\n\n"
                f"[bold]User Message:[/]\n{user_message}",
                title="Final Prompt",
                border_style="yellow"
            ))
        
        console.print("[bold green]Dry run completed. No LLM calls were made.[/]")
        raise typer.Exit()

    # ==================== NORMAL MODE ====================
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing PoCs...", total=len(urls))
        for i, poc_url in enumerate(urls, 1):
            progress.update(task, description=f"Processing {i}/{len(urls)} → [yellow]{poc_url[:70]}...[/]")

            user_message = f"""Analyze this Proof-of-Concept and generate the COMPLETE offensive security blueprint.

PoC URL: {poc_url}
Risk Level Preference: {risk_level}
Target OS: {target_os}
Include Mitigations: {include_mitigations}
Target Version: {target_version or 'Not specified'}

Follow the exact 7-phase pipeline in the system prompt. 
Apply the operator preferences above when generating the report.
Output ONLY the Markdown blueprint (no extra text)."""

            try:
                if verbose:
                    console.print(f"[dim]Calling {provider} with model: {model}[/]")

                blueprint = get_llm_response(
                    provider=provider,
                    api_key=api_key,
                    model=model,
                    temperature=temperature,
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

    console.print(Panel.fit(
        f"[bold green]✅ All done! {len(urls)} blueprint(s) saved to {output_dir}[/]",
        border_style="green"
    ))


if __name__ == "__main__":
    app()
