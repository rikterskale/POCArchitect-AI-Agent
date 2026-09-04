#!/usr/bin/env python3
"""Run selected no-network CLI examples that documentation treats as safe."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

GUIDE = ROOT / "docs" / "START_HERE.md"
RUNNER = CliRunner()
DOCUMENTED_COMMANDS = (
    "python -m pocarchitect --version",
    "python -m pocarchitect quickstart",
    "python -m pocarchitect doctor --offline",
    "python -m pocarchitect demo",
    "python -m pocarchitect preflight --offline --format json --no-color",
    "python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --format json --no-color",
    "python -m pocarchitect --format json --no-color batch-status --batch-state reports/batch_progress.json",
    "python -m pocarchitect --format json --no-color batch-reset --batch-state reports/batch_progress.json --yes",
    "pocarchitect setup",
    "pocarchitect config",
    "pocarchitect models",
    "pocarchitect history --output-dir reports",
    "pocarchitect diff reports/older-report.md reports/newer-report.md",
    "pocarchitect export reports/your-report.md --format html",
    "pocarchitect scaffold --report reports/your-report.md --output blueprint",
    "pocarchitect compare ./candidate-a ./candidate-b --output reports/comparison.md",
    "pocarchitect --help",
    "pocarchitect gui --help",
)


def validate_documented_commands(guide_text: str) -> list[str]:
    return [
        f"Canonical guide is missing selected safe command: {command}"
        for command in DOCUMENTED_COMMANDS
        if command not in guide_text
    ]


def run_safe_probes() -> list[str]:
    from pocarchitect import cli
    from pocarchitect.state import empty_state, write_state

    errors: list[str] = []
    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)
        state = temp / "batch_progress.json"
        output_dir = temp / "reports"
        output_dir.mkdir()
        write_state(state, empty_state())
        older = output_dir / "older-report.md"
        newer = output_dir / "newer-report.md"
        report = output_dir / "your-report.md"
        older.write_text("# Older\n", encoding="utf-8")
        newer.write_text("# Newer\n", encoding="utf-8")
        report.write_text("# Report\n", encoding="utf-8")
        candidate_a = temp / "candidate-a"
        candidate_b = temp / "candidate-b"
        candidate_a.mkdir()
        candidate_b.mkdir()
        (candidate_a / "app.py").write_text("print('a')\n", encoding="utf-8")
        (candidate_b / "app.js").write_text("console.log('b')\n", encoding="utf-8")

        original_cwd = Path.cwd()
        original_default_output = cli.default_output_dir
        original_get_output = cli.get_default_output_dir
        cli.default_output_dir = lambda: output_dir
        cli.get_default_output_dir = lambda: output_dir
        os.chdir(temp)
        probes = (
            (["--format", "json", "--no-color", "--version"], "version"),
            (
                [
                    "preflight",
                    "--offline",
                    "--output-dir",
                    str(output_dir),
                    "--format",
                    "json",
                    "--no-color",
                ],
                "preflight",
            ),
            (
                [
                    "--format",
                    "json",
                    "--no-color",
                    "doctor",
                    "--offline",
                    "--output-dir",
                    str(output_dir),
                ],
                "preflight",
            ),
            (["--format", "json", "--no-color", "demo"], "run_complete"),
            (["--format", "json", "--no-color", "quickstart"], "run_complete"),
            (
                [
                    "--url",
                    "https://github.com/example/poc",
                    "--no-ingest",
                    "--dry-run",
                    "--format",
                    "json",
                    "--no-color",
                ],
                "dry_run",
            ),
            (["--format", "json", "--no-color", "init"], "config_created"),
            (["--format", "json", "--no-color", "config"], "config"),
            (["--format", "json", "--no-color", "models"], "models"),
            (
                [
                    "--format",
                    "json",
                    "--no-color",
                    "history",
                    "--output-dir",
                    str(output_dir),
                ],
                "report_history",
            ),
            (
                [
                    "--format",
                    "json",
                    "--no-color",
                    "diff",
                    str(older),
                    str(newer),
                ],
                "report_diff",
            ),
            (
                [
                    "--format",
                    "json",
                    "--no-color",
                    "export",
                    str(report),
                    "--format",
                    "html",
                ],
                "report_exported",
            ),
            (
                [
                    "--format",
                    "json",
                    "--no-color",
                    "scaffold",
                    "--report",
                    str(report),
                    "--output",
                    str(temp / "blueprint"),
                ],
                "scaffold_created",
            ),
            (
                [
                    "--format",
                    "json",
                    "--no-color",
                    "compare",
                    str(candidate_a),
                    str(candidate_b),
                    "--output",
                    str(output_dir / "comparison.md"),
                ],
                "comparison_saved",
            ),
            (
                [
                    "--format",
                    "json",
                    "--no-color",
                    "batch-status",
                    "--batch-state",
                    str(state),
                ],
                "batch_status",
            ),
        )
        try:
            for arguments, expected_event in probes:
                result = RUNNER.invoke(cli.app, arguments)
                if result.exit_code != 0:
                    errors.append(
                        f"`python -m pocarchitect {' '.join(arguments)}` exited "
                        f"{result.exit_code}: {result.stdout.strip()}"
                    )
                    continue
                try:
                    events = [
                        json.loads(line)
                        for line in result.stdout.splitlines()
                        if line.startswith("{")
                    ]
                except json.JSONDecodeError as error:
                    errors.append(f"Safe probe emitted invalid JSON: {error}")
                    continue
                if not any(event.get("event") == expected_event for event in events):
                    errors.append(
                        f"Safe probe did not emit expected `{expected_event}` event: "
                        f"{' '.join(arguments)}"
                    )

            for arguments in (["--help"], ["gui", "--help"]):
                result = RUNNER.invoke(cli.app, arguments)
                if result.exit_code != 0 or "Usage:" not in result.stdout:
                    errors.append(f"Help probe failed: {' '.join(arguments)}")

            setup = RUNNER.invoke(cli.app, ["--format", "json", "--no-color", "setup"])
            if setup.exit_code != 2 or '"event": "error"' not in setup.stdout:
                errors.append("Non-interactive setup did not fail safely")

            reset = RUNNER.invoke(
                cli.app,
                [
                    "--format",
                    "json",
                    "--no-color",
                    "batch-reset",
                    "--batch-state",
                    str(state),
                    "--yes",
                ],
            )
            if reset.exit_code != 0:
                errors.append(f"Safe batch-reset probe failed: {reset.stdout.strip()}")
            else:
                payload = json.loads(reset.stdout)
                if payload.get("event") != "batch_reset":
                    errors.append("Safe batch-reset probe emitted the wrong event")
        finally:
            os.chdir(original_cwd)
            cli.default_output_dir = original_default_output
            cli.get_default_output_dir = original_get_output
    return errors


def main() -> int:
    errors = validate_documented_commands(GUIDE.read_text(encoding="utf-8"))
    errors.extend(run_safe_probes())
    if errors:
        print("Documentation command validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(
        "Credential-free documentation commands passed behavioral probes. "
        "Provider-backed commands remain external integration checks."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
