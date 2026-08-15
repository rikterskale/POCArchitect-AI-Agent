#!/usr/bin/env python3
"""Validate local Markdown links without requiring network access."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
DOC_DIRECTORIES = (ROOT / "docs", ROOT / "example_usage", ROOT / "pocarchitect")
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def markdown_files() -> list[Path]:
    files = set(ROOT.glob("*.md"))
    for directory in DOC_DIRECTORIES:
        if directory.exists():
            files.update(directory.rglob("*.md"))
    return sorted(files)


def normalize_anchor(value: str) -> str:
    return re.sub(r"[^a-z0-9 -]", "", value.lower()).replace(" ", "-")


def anchors(path: Path) -> set[str]:
    return {
        normalize_anchor(match.group(1))
        for match in re.finditer(
            r"^#{1,6}\s+(.+?)\s*$", path.read_text(encoding="utf-8"), re.MULTILINE
        )
    }


def validate_file(path: Path) -> list[str]:
    errors = []
    text = path.read_text(encoding="utf-8")
    for raw_target in MARKDOWN_LINK.findall(text):
        target = raw_target.split(maxsplit=1)[0].strip("<>")
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        location, separator, anchor = unquote(target).partition("#")
        destination = path if not location else (path.parent / location).resolve()
        if not destination.exists():
            errors.append(
                f"{path.relative_to(ROOT)}: missing link target `{raw_target}`"
            )
            continue
        if separator and anchor and destination.suffix.lower() == ".md":
            if normalize_anchor(anchor) not in anchors(destination):
                errors.append(
                    f"{path.relative_to(ROOT)}: missing anchor `{anchor}` in `{location or path.name}`"
                )
    return errors


def main() -> int:
    errors = [error for path in markdown_files() for error in validate_file(path)]
    if errors:
        print("Documentation link validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(
        f"Validated local Markdown targets and anchors in {len(markdown_files())} files. "
        "External reachability and behavioral accuracy are outside this check."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
