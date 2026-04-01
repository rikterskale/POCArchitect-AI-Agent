import typer
from pathlib import Path
from datetime import datetime
from openai import OpenAI
import importlib.resources
import os

app = typer.Typer(help="POCArchitect — Turn any POC URL into a perfect Markdown blueprint.")

def load_system_prompt() -> str:
    """Load the prompt from the package so it works after pip install."""
    with importlib.resources.files("pocarchitect").joinpath("prompt.md").open("r", encoding="utf-8") as f:
        return f.read()

@app.command()
def main(
    url: str = typer.Option(..., "--url", "-u", help="Single URL or path to batch_urls.txt"),
    provider: str = typer.Option("xai", "--provider", "-p", help="xai or openai"),
    api_key: str = typer.Option(..., "--api-key", "-k", help="API key"),
    model: str = typer.Option(None, "--model", "-m", help="Model name (default depends on provider)"),
    output_dir: Path = typer.Option(Path.cwd(), "--output-dir", "-o", help="Output directory"),
    temperature: float = typer.Option(0.0, "--temperature", "-t", help="Temperature (0.0 recommended)"),
):
    """Run POCArchitect on a URL or batch file."""
    
    # Set defaults
    if model is None:
        model = "grok-4" if provider == "xai" else "gpt-5-turbo"

    # Base URL for xAI
    base_url = "https://api.x.ai/v1" if provider == "xai" else None

    client = OpenAI(api_key=api_key, base_url=base_url)

    system_prompt = load_system_prompt()

    # Read input
    input_path = Path(url)
    if input_path.is_file() and input_path.suffix == ".txt":
        with open(input_path, "r", encoding="utf-8") as f:
            user_input = f.read().strip()
        is_batch = True
    else:
        user_input = url
        is_batch = False

    # Call the model
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        temperature=temperature,
    )

    output = response.choices[0].message.content

    # Save
    timestamp = datetime.now().strftime("%Y-%m-%d")
    reports_dir = output_dir / f"POCArchitect_Reports_{timestamp}"
    reports_dir.mkdir(parents=True, exist_ok=True)

    if is_batch:
        filename = reports_dir / "report_batch.md"  # model will create individual files + index inside
    else:
        # Simple slug for single report
        slug = url.split("/")[-1].replace(".git", "")[:50]
        filename = reports_dir / f"POCArchitect_Report_{slug}_{timestamp}.md"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(output)

    typer.echo(f"✅ Report saved: {filename}")

if __name__ == "__main__":
    app()