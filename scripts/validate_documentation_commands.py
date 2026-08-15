#!/usr/bin/env python3
"""Run selected no-network CLI examples that documentation treats as safe."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

GUIDE = ROOT / "docs" / "NOVICE_USABILITY_GUIDE.md"
RUNNER = CliRunner()
DOCUMENTED_COMMANDS = (
    "python -m pocarchitect --version",
    "python -m pocarchitect preflight --offline --format json --no-color",
    "python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --format json --no-color",
    "python -m pocarchitect --format json --no-color batch-status --batch-state reports/batch_progress.json",
    "python -m pocarchitect --format json --no-color batch-reset --batch-state reports/batch_progress.json --yes",
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
        write_state(state, empty_state())
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
    return errors


def main() -> int:
    errors = validate_documented_commands(GUIDE.read_text(encoding="utf-8"))
    errors.extend(run_safe_probes())
    if errors:
        print("Selected documentation command validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(
        "Selected no-network documentation commands passed. Commands outside "
        "this explicit probe set are not behaviorally validated here."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
