#!/usr/bin/env python3
import typer
import os
import tempfile
from pathlib import Path
from typing import Literal, Optional, List
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
                       no_ingest: bool):
    console.print(f"[bold cyan]Processing:[/] {url}")

    system_prompt = load_prompt()
    grounding = "" if no_ingest else build_grounding_context(url)

    user_message = f"""PoC URL: {url}

{grounding}

Operator Preferences (respect these exactly):
- Risk Level: {risk_level}
- Target OS / Environment: {target_os}
- Include Mitigations: {'Yes' if include_mitigations else 'No'}

MANDATORY: Base your entire report on the grounding context above. Quote real code, file names, and techniques from the provided files. Do not hallucinate or use general knowledge when specific content is available."""

    result = get_llm_response(
        provider=provider,
        api_key=api_key,
        model=model,
        temperature=temperature,
        base_url=base_url,
        system_prompt=system_prompt,
        user_message=user_message,
    )

    console.print(Panel(result[:500] + "..." if len(result) > 500 else result,
                        title="POC Architect Output", border_style="green"))
    return save_report(result, url, output_dir)


def generate_index_md(output_dir: Path, report_files: List[Path]):
    index_path = output_dir / "index.md"
    lines = ["# POCArchitect Batch Analysis Index\n"]
    lines.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append("## Reports\n")

    for report in report_files:
        relative = report.relative_to(output_dir)
        lines.append(f"- [{relative.name}]({relative})")

    index_path.write_text("\n".join(lines), encoding="utf-8")
    console.print(f"[green]Batch index created:[/] {index_path}")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    url: Optional[str] = typer.Option(None, "--url", "-u", help="Single PoC URL or path to .txt batch file (one URL per line)"),
    provider: str = typer.Option("xai", "--provider", "-p"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k"),
    base_url: Optional[str] = typer.Option(None, "--base-url"),
    model: str = typer.Option(None, "--model", "-m"),
    output_dir: Path = typer.Option(get_default_output_dir, "--output-dir", "-o"),
    temperature: float = typer.Option(0.0, "--temperature", "-t"),
    risk_level: Literal["Critical", "High", "Medium", "Low", "auto"] = typer.Option("auto", "--risk-level"),
    target_os: Literal["Windows", "Linux", "macOS", "cross-platform", "auto"] = typer.Option("auto", "--target-os"),
    include_mitigations: bool = typer.Option(True, "--include-mitigations", "--mitigations"),
    no_mitigations: bool = typer.Option(False, "--no-mitigations"),
    no_ingest: bool = typer.Option(False, "--no-ingest", help="Skip GitHub ingestion for very large repos"),
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

    if model is None:
        if provider.lower() == "openai":
            model = "gpt-4o"
        elif provider.lower() == "xai":
            model = "grok-4"
        else:
            model = "gpt-4o-mini"

    console.print("[bold cyan]POCArchitect AI Agent[/] — Starting...")

    if not dry_run:
        console.print("[bold cyan]🔍 Running preflight checks...[/]")
        run_preflight()

    input_path = Path(url)

    if input_path.is_file() and input_path.suffix.lower() in (".txt", ".list"):
        console.print(f"[bold magenta]Batch mode detected — processing file:[/] {input_path.name}")
        urls = [line.strip() for line in input_path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.strip().startswith("#")]

        if not urls:
            console.print("[bold red]Batch file is empty or contains only comments.[/]")
            raise typer.Exit(1)

        report_files: List[Path] = []
        for u in urls:
            report_path = process_single_url(
                url=u,
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
            )
            report_files.append(report_path)

        generate_index_md(output_dir, report_files)
        console.print(f"[bold green]✅ Batch complete — {len(urls)} reports generated[/]")
        raise typer.Exit(0)

    else:
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
        )


if __name__ == "__main__":
    app()