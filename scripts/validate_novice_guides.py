#!/usr/bin/env python3
"""Fail CI when the canonical Windows/Linux novice journeys lose key guidance."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDES = {
    "Windows": ROOT / "docs" / "guides" / "WINDOWS_NOVICE_USABILITY_GUIDE.md",
    "Linux": ROOT / "docs" / "guides" / "LINUX_NOVICE_USABILITY_GUIDE.md",
}
REQUIRED_COMMANDS = (
    "python -m pocarchitect --version",
    "python -m pocarchitect preflight --offline",
    "--no-ingest --dry-run",
    "batch-status",
    "batch-reset",
)


def validate_guide(platform: str, path: Path) -> list[str]:
    if not path.exists():
        return [f"{platform}: guide is missing: {path}"]
    text = path.read_text(encoding="utf-8")
    headings = re.findall(r"^##\s+.+$", text, flags=re.MULTILINE)
    errors = []
    if len(headings) < 30:
        errors.append(
            f"{platform}: expected at least 30 second-level journey headings; found {len(headings)}"
        )
    if "Status: **PARTIALLY VERIFIED**" not in text:
        errors.append(f"{platform}: must state its current validation status")
    if "## Command ledger" not in text:
        errors.append(f"{platform}: command ledger heading is missing")
    for command in REQUIRED_COMMANDS:
        if command not in text:
            errors.append(f"{platform}: required command missing from guide: {command}")
    prefix = "WIN" if platform == "Windows" else "LINUX"
    ledger_rows = re.findall(rf"\| {prefix}-\d{{2}} \|", text)
    if len(ledger_rows) < 5:
        errors.append(
            f"{platform}: expected at least five {prefix} command-ledger rows"
        )
    return errors


def main() -> int:
    errors = [
        error
        for platform, path in GUIDES.items()
        for error in validate_guide(platform, path)
    ]
    if errors:
        print("Novice guide validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("Novice guides are complete and command-ledger validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
