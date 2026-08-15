#!/usr/bin/env python3
"""Validate local Markdown targets inside the built source distribution."""

from __future__ import annotations

import argparse
import posixpath
import re
import tarfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def normalize_anchor(value: str) -> str:
    return re.sub(r"[^a-z0-9 -]", "", value.lower()).replace(" ", "-")


def validate_sdist(path: Path) -> list[str]:
    errors: list[str] = []
    with tarfile.open(path, "r:gz") as archive:
        members = {
            PurePosixPath(member.name): member
            for member in archive.getmembers()
            if member.isfile()
        }
        roots = {member.parts[0] for member in members if member.parts}
        if len(roots) != 1:
            return [f"Expected one source-distribution root, found {sorted(roots)}"]
        root = next(iter(roots))
        relative_members = {
            PurePosixPath(*member.parts[1:]): info for member, info in members.items()
        }
        required = (
            PurePosixPath("README.md"),
            PurePosixPath("docs/DOCUMENTATION_GAP_ANALYSIS.md"),
            PurePosixPath("docs/DOCUMENTATION_REVIEW_REPORT.md"),
        )
        for required_path in required:
            if required_path not in relative_members:
                errors.append(f"Source distribution is missing `{required_path}`")

        markdown_text: dict[PurePosixPath, str] = {}
        for member, info in relative_members.items():
            if member.suffix.lower() != ".md":
                continue
            extracted = archive.extractfile(info)
            if extracted is None:
                errors.append(f"Could not read `{root}/{member}`")
                continue
            markdown_text[member] = extracted.read().decode("utf-8")

        for source, text in markdown_text.items():
            for raw_target in MARKDOWN_LINK.findall(text):
                target = raw_target.split(maxsplit=1)[0].strip("<>")
                if not target or target.startswith(("http://", "https://", "mailto:")):
                    continue
                location, separator, anchor = unquote(target).partition("#")
                destination = (
                    source
                    if not location
                    else PurePosixPath(
                        posixpath.normpath(str(source.parent / location))
                    )
                )
                if destination not in relative_members:
                    errors.append(
                        f"{source}: missing packaged link target `{raw_target}`"
                    )
                    continue
                if separator and anchor and destination in markdown_text:
                    headings = {
                        normalize_anchor(match.group(1))
                        for match in re.finditer(
                            r"^#{1,6}\s+(.+?)\s*$",
                            markdown_text[destination],
                            re.MULTILINE,
                        )
                    }
                    if normalize_anchor(anchor) not in headings:
                        errors.append(
                            f"{source}: missing packaged anchor `{anchor}` in `{destination}`"
                        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dist", nargs="?", type=Path, default=Path("dist"))
    args = parser.parse_args()
    archives = sorted(args.dist.glob("*.tar.gz"))
    if len(archives) != 1:
        print(
            f"Expected exactly one source distribution in {args.dist}; "
            f"found {len(archives)}."
        )
        return 1
    errors = validate_sdist(archives[0])
    if errors:
        print("Source-distribution documentation validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(
        f"Validated packaged local Markdown targets in {archives[0].name}; "
        "external reachability and behavioral accuracy are outside this check."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
