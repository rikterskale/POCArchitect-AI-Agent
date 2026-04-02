#!/usr/bin/env python3
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import print as rprint
from openai import OpenAI
from pathlib import Path

# Create the Typer app
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
        console.print("[bold red]❌ POC_Architect_Prompt.md not found![/]", style="bold red")
        raise typer.Exit(1)
    return prompt_path.read_text(encoding="utf-8")


def get_client(provider: str, api_key: str):
    """Create OpenAI-compatible client for xAI or OpenAI."""
    if provider.lower() == "xai":
        return OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
        )
    elif provider.lower() == "openai":
        return OpenAI(api_key=api_key)
    else:
        console.print(f"[bold red]❌ Unsupported provider: {provider}[/]", style="bold red")
        raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    url: str = typer.Option(..., "--url", "-u", help="Single PoC URL or path to batch_urls.txt"),
    provider: str = typer.Option("xai", "--provider", "-p", help="LLM provider: xai or openai"),
    api_key: str = typer.Option(
        ...,
        "--api-key",
        "-k",
        help="API key (or set XAI_API_KEY / OPENAI_API_KEY in .env)",
        envvar=["XAI_API_KEY", "OPENAI_API_KEY"],
    ),
    model: str = typer.Option("grok-4", "--model", "-m", help="Model name to use"),
    output_dir: Path = typer.Option(
        Path.cwd() / "reports", "--output-dir", "-o", help="Output directory"
    ),
    temperature: float = typer.Option(0.0, "--temperature", "-t", help="Temperature (0.0 recommended for consistency)"),
    version: bool = typer.Option(False, "--version", "-v", help="Show version and exit"),
):
    """Generate full offensive security blueprints from PoC URLs."""

    if version:
        try:
            from pocarchitect import __version__
            console.print(f"[bold cyan]POCArchitect[/bold cyan] v{__version__}")
        except ImportError:
            console.print("[bold cyan]POCArchitect[/bold cyan] (version unknown)")
        raise typer.Exit()

    # Safety: if user ran "pocarchitect" with no arguments at all, show help
    if ctx.invoked_subcommand is None and not ctx.args and not ctx.params.get("url"):
        typer.echo(ctx.get_help())
        raise typer.Exit()

    console.print(
        Panel.fit(
            "[bold green]🚀 POCArchitect AI Agent[/] — Forging blueprints of digital domination",
            border_style="green"
        )
    )

    prompt = load_prompt()
    client = get_client(provider, api_key)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Handle batch vs single
    urls: list[str] = []
    input_path = Path(url)
    if input_path.exists() and (input_path.suffix in (".txt", "") or input_path.is_dir()):
        content = input_path.read_text(encoding="utf-8")
        urls = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]
        console.print(f"[cyan]📦 Batch mode — {len(urls)} URLs loaded[/]")
    else:
        urls = [url]

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
Follow the exact 7-phase pipeline in the system prompt. Output ONLY the Markdown blueprint (no extra text)."""

            try:
                response = client.chat.completions.create(
                    model=model,
                    temperature=temperature,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": user_message},
                    ],
                )
                blueprint = response.choices[0].message.content.strip()

                safe_name = poc_url.split("/")[-1].replace(".git", "").replace("/", "_")[:100]
                output_path = output_dir / f"POC_Blueprint_{safe_name}.md"

                output_path.write_text(blueprint, encoding="utf-8")
                rprint(f"[bold green]✅ Saved:[/] [cyan]{output_path.name}[/]")

            except Exception as e:
                console.print(f"[bold red]❌ Failed {poc_url}:[/] {e}")

            progress.advance(task)

    console.print(Panel.fit("[bold green]🎉 All blueprints generated![/]", border_style="green"))
    console.print(f"📁 Output folder: [bold]{output_dir}[/]")


if __name__ == "__main__":
    app()
