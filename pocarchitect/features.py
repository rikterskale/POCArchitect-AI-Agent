"""Product features shared by the CLI without coupling them to Typer.

The helpers in this module are deliberately deterministic and provider-neutral so
they can be used by dry-runs, CI jobs, plugins, and the interactive presentation.
"""

from __future__ import annotations

import html
import json
import os
import re
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import unified_diff
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, Protocol

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from .file_io import (
    harden_private_descriptor,
    harden_private_path,
)
from .verification import CONTRACT_FILENAME, create_contract

CONFIG_FILE = ".pocarchitect.toml"
HISTORY_FILE = "history.json"
DEFAULT_PROJECT_CONFIG: dict[str, Any] = {
    "provider": "xai",
    "risk_level": "High",
    "target_os": "Linux",
    "include_mitigations": True,
    "output_dir": "reports",
    "report_format": "markdown",
}


def classify_source(value: str) -> str:
    candidate = value.strip()
    if Path(candidate).exists():
        return "local-directory" if Path(candidate).is_dir() else "local-file"
    lowered = candidate.lower()
    if lowered.startswith(("pypi:", "pypi://")):
        return "pypi-package"
    if lowered.startswith(("npm:", "npm://")):
        return "npm-package"
    if lowered.startswith(("docker:", "docker://")):
        return "docker-image"
    if "github.com/" in lowered:
        return "github-repository"
    if lowered.startswith(("http://", "https://")) and lowered.endswith(
        (".tar", ".tar.gz", ".tgz", ".zip")
    ):
        return "archive-url"
    if lowered.startswith(("http://", "https://")):
        return "download-url"
    return "identifier"


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.startswith(('"', "'")) and value.endswith(('"', "'")):
        return value[1:-1]
    try:
        return float(value) if "." in value else int(value)
    except ValueError:
        return value


def load_project_config(
    start: Path | None = None,
) -> tuple[dict[str, Any], Path | None]:
    """Load the nearest project config, walking upward from *start*."""
    current = (start or Path.cwd()).resolve()
    candidates = [current, *current.parents]
    for directory in candidates:
        path = directory / CONFIG_FILE
        if not path.is_file():
            continue
        values: dict[str, Any] = {}
        section = ""
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1].strip()
                continue
            if "=" in line and section in {"", "defaults"}:
                key, value = line.split("=", 1)
                values[key.strip()] = _parse_scalar(value)
        return {**DEFAULT_PROJECT_CONFIG, **values}, path
    return dict(DEFAULT_PROJECT_CONFIG), None


def write_project_config(path: Path, *, overwrite: bool = False) -> Path:
    if path.exists() and not overwrite:
        raise FileExistsError(path)
    text = """# POCArchitect per-repository defaults
[defaults]
provider = "xai"
risk_level = "High"
target_os = "Linux"
include_mitigations = true
output_dir = "reports"
report_format = "markdown"
"""
    path.write_text(text, encoding="utf-8")
    return path


@dataclass
class PhaseTimings:
    """Collect elapsed time per run phase and expose stable JSON data."""

    started: float = field(default_factory=time.monotonic)
    durations: dict[str, float] = field(default_factory=dict)

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        phase_start = time.monotonic()
        try:
            yield
        finally:
            self.durations[name] = self.durations.get(name, 0.0) + (
                time.monotonic() - phase_start
            )

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.started

    def rounded(self) -> dict[str, float]:
        return {name: round(seconds, 3) for name, seconds in self.durations.items()}


def mock_report(url: str, risk_level: str, target_os: str, mitigations: bool) -> str:
    mitigation = (
        "## Mitigations\n\n- Validate the finding in an isolated lab.\n"
        "- Patch affected components and restrict exposure.\n"
        if mitigations
        else ""
    )
    return f"""# PoC Architecture Report (Preview)

> Dry-run preview only — no provider call was made.

## Executive Summary

Source: `{url}`  
Requested risk posture: **{risk_level}**  
Target environment: **{target_os}**

## Architecture

```mermaid
flowchart LR
    Source[Source input] --> Ingest[Safe ingestion]
    Ingest --> Analyze[Analysis provider]
    Analyze --> Report[Reproducible blueprint]
```

## Findings

### [Preview] Primary technical finding

- Severity: {risk_level}
- Evidence: populated from selected source files in a real run
- Reproduction: generated as safe, environment-specific steps

{mitigation}## Reproducible Blueprint

The real report includes prerequisites, architecture, validation, and next steps.
"""


def architecture_diagram(file_names: list[str]) -> str:
    """Infer a conservative Mermaid diagram from selected repository paths."""
    groups: list[tuple[str, str]] = []
    lowered = [name.lower() for name in file_names]
    if any("docker" in name or name.endswith((".yml", ".yaml")) for name in lowered):
        groups.append(("Config", "Configuration / runtime"))
    if any(name.endswith((".py", ".go", ".rs", ".c", ".cpp")) for name in lowered):
        groups.append(("Core", "Application / PoC logic"))
    if any("test" in name for name in lowered):
        groups.append(("Tests", "Validation"))
    if any("readme" in name or name.endswith(".md") for name in lowered):
        groups.append(("Docs", "Documentation"))
    if not groups:
        groups.append(("Source", "Source material"))
    lines = [
        "```mermaid",
        "flowchart LR",
        "    Entry[Operator] --> Input[Source input]",
    ]
    previous = "Input"
    for node, label in groups:
        lines.append(f"    {previous} --> {node}[{label}]")
        previous = node
    lines.append(f"    {previous} --> Report[Architecture report]")
    lines.append("```")
    return "\n".join(lines)


def ensure_architecture_section(report: str, file_names: list[str]) -> str:
    if "```mermaid" in report or "```plantuml" in report:
        return report
    return (
        report.rstrip()
        + "\n\n## Inferred Architecture\n\n"
        + architecture_diagram(file_names)
        + "\n"
    )


def parse_report_metrics(content: str) -> dict[str, Any]:
    headings = re.findall(r"(?m)^###?\s+(.+)$", content)
    finding_heads = [
        h
        for h in headings
        if not re.match(r"(?i)(mitigation|architecture|blueprint|summary)", h)
    ]
    risks = re.findall(
        r"(?im)(?:severity|risk(?: level)?)\s*[:|]\s*\*{0,2}(critical|high|medium|low)",
        content,
    )
    mitigation_count = len(
        re.findall(
            r"(?im)^\s*[-*]\s+.*(?:patch|restrict|validate|mitigat|upgrade|disable)",
            content,
        )
    )
    return {
        "findings_count": len(finding_heads),
        "top_risks": risks[:3],
        "mitigations_count": mitigation_count,
    }


def render_summary_card(
    console: Console,
    content: str,
    report_path: Path,
    estimated_cost: float | None,
) -> None:
    metrics = parse_report_metrics(content)
    table = Table.grid(padding=(0, 2))
    table.add_column(style="cyan")
    table.add_column()
    table.add_row("Findings", str(metrics["findings_count"]))
    table.add_row("Top risks", ", ".join(metrics["top_risks"]) or "See report")
    table.add_row("Mitigations", str(metrics["mitigations_count"]))
    table.add_row(
        "Estimated input cost",
        f"${estimated_cost:.4f}" if estimated_cost is not None else "Unavailable",
    )
    table.add_row("Report", str(report_path.resolve()))
    table.add_row(
        "Next", f"pocarchitect history  •  pocarchitect scaffold --report {report_path}"
    )
    console.print(
        Panel(table, title="Run complete", border_style="green", expand=False)
    )


def render_dashboard(
    console: Console,
    phases: dict[str, float],
    file_names: list[str],
    report: str,
) -> None:
    layout = Layout()
    layout.split_row(Layout(name="left", ratio=1), Layout(name="preview", ratio=2))
    layout["left"].split_column(Layout(name="progress"), Layout(name="files"))
    phase_lines = (
        "\n".join(f"✓ {name:<12} {seconds:.2f}s" for name, seconds in phases.items())
        or "Starting…"
    )
    file_lines = "\n".join(f"• {name}" for name in file_names[:18]) or "URL-only input"
    layout["progress"].update(Panel(phase_lines, title="Run progress"))
    layout["files"].update(
        Panel(file_lines, title=f"Grounding files ({len(file_names)})")
    )
    preview = "\n".join(report.splitlines()[:35])
    layout["preview"].update(Panel(preview, title="Report preview"))
    console.print(layout)


class LiveRunDashboard:
    """Three-pane live run view for an interactive terminal."""

    def __init__(self, console: Console, enabled: bool) -> None:
        self.console = console
        self.enabled = enabled
        self.phases: dict[str, str] = {}
        self.files: list[str] = []
        self.report = "Waiting for report output…"
        self._live: Live | None = None

    def _layout(self) -> Layout:
        layout = Layout()
        layout.split_row(Layout(name="left", ratio=1), Layout(name="preview", ratio=2))
        layout["left"].split_column(Layout(name="progress"), Layout(name="files"))
        phase_lines = (
            "\n".join(f"{state} {name}" for name, state in self.phases.items())
            or "◌ Starting…"
        )
        file_lines = (
            "\n".join(f"• {name}" for name in self.files[:18])
            or "Discovering source files…"
        )
        layout["progress"].update(Panel(phase_lines, title="Live run progress"))
        layout["files"].update(
            Panel(file_lines, title=f"Grounding files ({len(self.files)})")
        )
        layout["preview"].update(
            Panel("\n".join(self.report.splitlines()[:35]), title="Report preview")
        )
        return layout

    def start(self) -> None:
        if self.enabled and self._live is None:
            self._live = Live(
                self._layout(), console=self.console, refresh_per_second=8
            )
            self._live.start()

    def phase(self, name: str, *, complete: bool = False) -> None:
        if self.enabled:
            self.phases[name] = "✓" if complete else "⠋"
            self.refresh()

    def set_files(self, names: list[str]) -> None:
        self.files = names
        self.refresh()

    def set_report(self, report: str) -> None:
        self.report = report
        self.refresh()

    def refresh(self) -> None:
        if self._live is not None:
            self._live.update(self._layout(), refresh=True)

    def stop(self) -> None:
        if self._live is not None:
            self._live.update(self._layout(), refresh=True)
            self._live.stop()
            self._live = None


def _report_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---\n") and "\n---\n" in text[4:]:
        return text.split("\n---\n", 1)[1].lstrip()
    return text


def _write_private_bytes(path: Path, content: bytes) -> None:
    """Atomically write report output without following a destination symlink."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        harden_private_descriptor(descriptor)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        harden_private_path(path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary_path.unlink(missing_ok=True)


def _write_private_text(path: Path, content: str) -> None:
    """Atomically write UTF-8 report output with private permissions."""
    _write_private_bytes(path, content.encode("utf-8"))


def report_diff(previous: Path, current: Path) -> str:
    before = _report_body(previous).splitlines()
    after = _report_body(current).splitlines()
    changes = unified_diff(
        before, after, fromfile=previous.name, tofile=current.name, lineterm=""
    )
    return "\n".join(changes)


def read_report_metadata(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        return {}
    block = text[4:].split("\n---\n", 1)[0]
    result: dict[str, Any] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        try:
            result[key.strip()] = json.loads(raw.strip())
        except json.JSONDecodeError:
            result[key.strip()] = raw.strip()
    return result


def find_previous_report(output_dir: Path, source: str) -> Path | None:
    matches: list[Path] = []
    for path in output_dir.glob("POCAnalysis_*.md"):
        try:
            if read_report_metadata(path).get("source_url") == source:
                matches.append(path)
        except OSError:
            continue
    return max(matches, key=lambda item: item.stat().st_mtime) if matches else None


def update_history(output_dir: Path, report_path: Path) -> Path:
    history_path = output_dir / HISTORY_FILE
    try:
        data = (
            json.loads(history_path.read_text(encoding="utf-8"))
            if history_path.exists()
            else {"version": 1, "reports": []}
        )
    except (OSError, json.JSONDecodeError):
        data = {"version": 1, "reports": []}
    if not isinstance(data, dict):
        data = {"version": 1, "reports": []}
    metadata = read_report_metadata(report_path)
    reports = data.setdefault("reports", [])
    if not isinstance(reports, list):
        reports = []
        data["reports"] = reports
    reports.append({"path": str(report_path), **metadata})
    _write_private_text(history_path, json.dumps(data, indent=2, sort_keys=True) + "\n")
    return history_path


def _write_simple_pdf(target: Path, content: str) -> None:
    """Write a dependency-free text PDF suitable for portable report sharing."""
    clean = content.encode("ascii", "replace").decode("ascii")
    lines: list[str] = []
    for raw in clean.splitlines():
        while len(raw) > 92:
            lines.append(raw[:92])
            raw = raw[92:]
        lines.append(raw)
    pages = [
        lines[index : index + 52] for index in range(0, max(1, len(lines)), 52)
    ] or [[]]
    objects: list[bytes] = []
    page_ids: list[int] = []
    # Objects 1 and 2 are catalog and pages; object 3 is the shared font.
    objects.extend(
        (
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
        )
    )
    for page in pages:
        page_id = len(objects) + 1
        content_id = page_id + 1
        page_ids.append(page_id)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>".encode()
        )
        commands = ["BT /F1 9 Tf 36 756 Td 11 TL"]
        for line in page:
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            commands.append(f"({escaped}) Tj T*")
        commands.append("ET")
        stream = "\n".join(commands).encode("ascii")
        objects.append(
            b"<< /Length "
            + str(len(stream)).encode()
            + b" >>\nstream\n"
            + stream
            + b"\nendstream"
        )
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode()
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    _write_private_bytes(target, bytes(output))


def export_report(markdown_path: Path, output_format: str) -> Path:
    """Export one report to HTML, PDF, or structured JSON."""
    content = _report_body(markdown_path)
    metadata = read_report_metadata(markdown_path)
    if output_format == "markdown":
        return markdown_path
    if output_format == "json":
        target = markdown_path.with_suffix(".json")
        _write_private_text(
            target,
            json.dumps(
                {
                    "metadata": metadata,
                    "content": content,
                    "metrics": parse_report_metrics(content),
                },
                indent=2,
            )
            + "\n",
        )
        return target
    if output_format == "html":
        target = markdown_path.with_suffix(".html")
        escaped = html.escape(content)
        document = f"""<!doctype html><html><head><meta charset=\"utf-8\"><title>{html.escape(markdown_path.stem)}</title>
<style>body{{font:16px/1.55 system-ui;max-width:960px;margin:3rem auto;padding:0 1rem;background:#10151c;color:#e7edf4}}pre{{white-space:pre-wrap;background:#18212c;padding:1.5rem;border-radius:10px}}</style></head>
<body><h1>{html.escape(markdown_path.stem)}</h1><pre>{escaped}</pre></body></html>"""
        _write_private_text(target, document)
        return target
    if output_format == "pdf":
        target = markdown_path.with_suffix(".pdf")
        _write_simple_pdf(target, content)
        return target
    raise ValueError(f"Unsupported report format: {output_format}")


def extract_implementation_bundle(content: str) -> dict[Path, str]:
    """Extract strictly named files from the report's implementation section."""
    section = re.compile(
        r"^(#{2,3})\s+(?:Phase\s+8\s*[-–—:]\s*)?(?:Full Weaponized Artifact|Implementation Bundle)\s*$",
        re.IGNORECASE,
    )
    file_header = re.compile(r"^#{3,6}\s+File:\s+(.+?)\s*$", re.IGNORECASE)
    files: dict[Path, str] = {}
    active = False
    section_level = 0
    selected: Path | None = None
    fence: str | None = None
    captured: list[str] = []
    total_bytes = 0

    for line in content.splitlines():
        if not active:
            section_match = section.match(line.strip())
            active = bool(section_match)
            if section_match:
                section_level = len(section_match.group(1))
            continue
        if fence is None:
            heading = re.match(r"^(#{1,6})\s+", line)
            if heading and len(heading.group(1)) <= section_level:
                break
            match = file_header.match(line.strip())
            if match:
                candidate = match.group(1).strip().strip("`").replace("\\", "/")
                path = Path(candidate)
                lowered = {part.lower() for part in path.parts}
                if (
                    not candidate
                    or len(candidate) > 240
                    or path.is_absolute()
                    or re.match(r"^[A-Za-z]:", candidate)
                    or ".." in path.parts
                    or lowered.intersection({".git", ".ssh", ".aws", ".pocarchitect"})
                    or path.name == ".env"
                    or (path.name.startswith(".env.") and path.name != ".env.example")
                    or path.name.lower()
                    in {CONTRACT_FILENAME, "blueprint.json", "pocarchitect.md"}
                ):
                    raise ValueError(f"Unsafe implementation bundle path: {candidate}")
                if path in files:
                    raise ValueError(
                        f"Duplicate implementation bundle path: {candidate}"
                    )
                selected = path
                continue
            if selected is not None:
                opening = re.match(r"^(`{3,}|~{3,})", line.strip())
                if opening:
                    fence = opening.group(1)
                    captured = []
            continue
        if line.strip().startswith(fence):
            if selected is None:
                raise ValueError(
                    "Implementation bundle parser reached a fence without a file path."
                )
            text = "\n".join(captured) + "\n"
            total_bytes += len(text.encode("utf-8"))
            if len(files) >= 50 or total_bytes > 512 * 1024:
                raise ValueError(
                    "Implementation bundle exceeds the 50-file/512-KiB limit."
                )
            files[selected] = text
            selected = None
            fence = None
            captured = []
        else:
            captured.append(line)
    if fence is not None:
        raise ValueError("Implementation bundle contains an unterminated code fence.")
    return files


def create_scaffold(report_path: Path, destination: Path) -> list[Path]:
    """Materialize a candidate implementation with an initially draft test contract."""
    implementation = extract_implementation_bundle(_report_body(report_path))
    destination = Path(os.path.abspath(os.fspath(destination.expanduser())))
    if destination.is_symlink():
        raise ValueError(f"Scaffold destination cannot be a symlink: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    control_directory = destination / ".pocarchitect"
    if control_directory.is_symlink():
        raise ValueError(
            f"Scaffold path cannot traverse a symlink: {control_directory}"
        )
    metrics = parse_report_metrics(_report_body(report_path))
    files = {
        destination
        / "README.md": (
            f"# {destination.name}\n\nGenerated from `{report_path.name}`.\n\n"
            f"## Candidate implementation\n\nPOCArchitect materialized {len(implementation)} "
            "strictly named implementation file(s) from the report. Generated code is a "
            "candidate, not proof that the PoC works. Review every file and replace or add "
            "meaningful acceptance tests.\n\n"
            "Review `.pocarchitect/poc-verification.json`, document "
            "the authorized lab scope, and change `implementation_status` to `ready`.\n\n"
            "Then run `pocarchitect verify run . --yes`. POCArchitect only labels the "
            "result VERIFIED after every contracted build, test, and artifact check passes "
            "inside its isolated Docker sandbox.\n"
        ),
        destination / ".gitignore": ".venv/\n__pycache__/\n.env\n",
        destination
        / "POCARCHITECT.md": (
            "# Verification gate\n\nGenerated code is a candidate until the explicit "
            "contract passes. Review every file and test, document the authorized lab "
            "scope in `.pocarchitect/poc-verification.json`, set "
            "`implementation_status` to `ready`, ensure the declared Docker image is "
            "reviewed and present locally, then run:\n\n"
            "```text\npocarchitect verify run . --yes\n```\n\n"
            "Only a `poc_verified` result with retained JSON evidence supports a working-PoC claim.\n"
        ),
        destination
        / "blueprint.json": json.dumps(
            {
                "source_report": str(report_path),
                "metrics": metrics,
                "implementation_files": sorted(
                    path.as_posix() for path in implementation
                ),
            },
            indent=2,
        )
        + "\n",
    }
    if implementation:
        files.update(
            {destination / path: content for path, content in implementation.items()}
        )
    else:
        files.update(
            {
                destination
                / "pyproject.toml": (
                    '[project]\nname = "poc-blueprint"\nversion = "0.1.0"\n'
                    'requires-python = ">=3.10"\ndependencies = []\n'
                ),
                destination
                / "src"
                / "poc_blueprint"
                / "__init__.py": '"""Authorized PoC implementation package."""\n',
                destination
                / "tests"
                / "test_implementation.py": (
                    "import unittest\n\n\n"
                    "class ImplementationAcceptanceTest(unittest.TestCase):\n"
                    "    def test_authorized_poc_behavior(self):\n"
                    '        self.fail("Replace this placeholder with a meaningful lab assertion.")\n'
                ),
            }
        )
    contract = control_directory / CONTRACT_FILENAME
    # Preflight the complete write set before materializing any file so a
    # conflicting symlink cannot leave a misleading partial scaffold behind.
    for path in [*files, contract]:
        current = destination
        for part in path.relative_to(destination).parts[:-1]:
            current /= part
            if current.is_symlink():
                raise ValueError(f"Scaffold path cannot traverse a symlink: {current}")
            if current.exists() and not current.is_dir():
                raise ValueError(f"Scaffold parent is not a directory: {current}")
        if path.is_symlink():
            raise ValueError(f"Scaffold file cannot replace a symlink: {path}")
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            _write_private_text(path, content)
    if not contract.exists():
        create_contract(destination, contract)
    return [*files, contract]


class AnalyzerPlugin(Protocol):
    name: str

    def analyze(self, source: str, grounding: str) -> str:
        """Return analyzer output for the supplied source and grounding context."""
        raise TypeError("AnalyzerPlugin is a protocol contract")


_PLUGINS: dict[str, AnalyzerPlugin] = {}
_PLUGINS_DISCOVERED = False


def register_plugin(plugin: AnalyzerPlugin) -> None:
    if not getattr(plugin, "name", ""):
        raise ValueError("Analyzer plugins require a non-empty name")
    _PLUGINS[plugin.name] = plugin


def discover_plugins() -> None:
    """Load installed ``pocarchitect.analyzers`` entry points once."""
    global _PLUGINS_DISCOVERED
    if _PLUGINS_DISCOVERED:
        return
    _PLUGINS_DISCOVERED = True
    selected = entry_points(group="pocarchitect.analyzers")
    for entry_point in selected:
        try:
            plugin = entry_point.load()
            register_plugin(plugin() if isinstance(plugin, type) else plugin)
        except Exception:  # noqa: BLE001, S112 - third-party discovery is isolated
            # A third-party plugin must not prevent core analysis from running.
            continue  # nosec B112


def registered_plugins() -> list[str]:
    discover_plugins()
    return sorted(_PLUGINS)


def run_plugins(source: str, grounding: str) -> list[str]:
    sections: list[str] = []
    for name in registered_plugins():
        try:
            sections.append(_PLUGINS[name].analyze(source, grounding))
        except Exception:  # noqa: BLE001, S112 - third-party execution is isolated
            # Analyzer failures are isolated so one plugin cannot abort the run.
            continue  # nosec B112
    return sections


def history_rows(output_dir: Path) -> list[dict[str, Any]]:
    path = output_dir / HISTORY_FILE
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("reports"), list):
            return []
        return [row for row in data["reports"] if isinstance(row, dict)]
    except (OSError, json.JSONDecodeError, TypeError):
        return []


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
