#!/usr/bin/env python3
"""Validate canonical-guide structure and platform-delta command ledgers."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDES = {
    "Windows": ROOT / "docs" / "guides" / "WINDOWS_NOVICE_USABILITY_GUIDE.md",
    "Linux": ROOT / "docs" / "guides" / "LINUX_NOVICE_USABILITY_GUIDE.md",
}
CANONICAL_GUIDE = ROOT / "docs" / "NOVICE_USABILITY_GUIDE.md"
REQUIRED_CANONICAL_HEADINGS = (
    "## 1. What This Guide Helps You Do",
    "## 6. Before You Begin",
    "## 9. Obtain or Clone the Repository",
    "## 12. Install Project Dependencies",
    "## 15. Run the Safest First Example",
    "## 16. Verify the First Run Succeeded",
    "## 17. If Verification Fails: Diagnose and Fix It",
    "## 25. Troubleshooting Matrix",
    "## 29. Glossary",
)
REQUIRED_COMMANDS = (
    "python -m pocarchitect --version",
    "python -m pocarchitect preflight --offline",
    "--no-ingest --dry-run",
    "batch-status",
    "batch-reset",
)
PLATFORM_REQUIREMENTS = {
    "Windows": {
        "prefix": "WIN",
        "needles": (
            "PowerShell",
            r".\.venv\Scripts\Activate.ps1",
            r".\reports\batch_progress.json",
            "preflight --provider openai",
            "preflight --provider local --base-url",
        ),
    },
    "Linux": {
        "prefix": "LINUX",
        "needles": (
            "Bash",
            ". .venv/bin/activate",
            "./reports/batch_progress.json",
            "preflight --provider openai",
            "preflight --provider local --base-url",
        ),
    },
}


def validate_guide(platform: str, path: Path) -> list[str]:
    if not path.exists():
        return [f"{platform}: guide is missing: {path}"]
    text = path.read_text(encoding="utf-8")
    errors = []
    if "Status: **PARTIALLY VERIFIED**" not in text:
        errors.append(f"{platform}: must state its current validation status")
    if "[Novice Usability Guide](../NOVICE_USABILITY_GUIDE.md)" not in text:
        errors.append(f"{platform}: canonical-guide link is missing")
    if "## Command ledger" not in text:
        errors.append(f"{platform}: command ledger heading is missing")
    requirements = PLATFORM_REQUIREMENTS[platform]
    for needle in requirements["needles"]:
        if needle not in text:
            errors.append(f"{platform}: required platform delta missing: {needle}")
    prefix = requirements["prefix"]
    ledger_rows = re.findall(rf"\| {prefix}-\d{{2}} \|", text)
    if len(ledger_rows) < 5:
        errors.append(
            f"{platform}: expected at least five {prefix} command-ledger rows"
        )
    return errors


def validate_canonical_guide(path: Path) -> list[str]:
    if not path.exists():
        return [f"Canonical guide is missing: {path}"]
    text = path.read_text(encoding="utf-8")
    errors = []
    if "**PARTIALLY VERIFIED**" not in text:
        errors.append("Canonical guide must state its current validation status")
    for heading in REQUIRED_CANONICAL_HEADINGS:
        if heading not in text:
            errors.append(f"Canonical guide is missing required heading: {heading}")
    for command in REQUIRED_COMMANDS:
        if command not in text:
            errors.append(f"Canonical guide is missing required command: {command}")
    if "https://github.com/example/poc" not in text:
        errors.append("Canonical guide is missing the safe example URL")
    return errors


def main() -> int:
    errors = [
        error
        for platform, path in GUIDES.items()
        for error in validate_guide(platform, path)
    ]
    errors.extend(validate_canonical_guide(CANONICAL_GUIDE))
    if errors:
        print("Novice guide validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(
        "Novice guide structure and platform-delta command ledgers are present. "
        "This structural check does not prove command behavior."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
