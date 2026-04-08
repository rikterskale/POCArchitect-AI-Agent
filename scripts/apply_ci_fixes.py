#!/usr/bin/env python3
"""Apply CI-related compatibility fixes to POCArchitect files.

This patcher is idempotent and can be run multiple times safely.
"""

from __future__ import annotations

import argparse
from pathlib import Path


CI_YML = """name: Build and Test

on:
  push:
    branches:
      - main
  pull_request:

env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: [\"3.10\", \"3.11\", \"3.12\", \"3.13\"]

    steps:
      - name: Checkout repository
        uses: actions/checkout@v5

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
          cache-dependency-path: |
            requirements.txt
            requirements-dev.txt
            pyproject.toml

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt
          pip install -e .
          pip install build

      - name: Run tests
        run: pytest

      - name: Check formatting
        run: ruff format --check .

      - name: Build package
        run: python -m build
"""


def replace_once(text: str, old: str, new: str) -> tuple[str, bool]:
    if old in text:
        return text.replace(old, new, 1), True
    return text, False


def read_text_with_fallback(path: Path) -> str:
    """Read text robustly across mixed local encodings (UTF-8/Windows legacy)."""
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    # Last resort: preserve file content as best-effort replacement.
    return path.read_text(encoding="utf-8", errors="replace")


def patch_cli(text: str) -> tuple[str, int]:
    changes = 0

    if "import subprocess\n" not in text:
        text, changed = replace_once(
            text, "import tempfile\n", "import tempfile\nimport subprocess\n"
        )
        changes += int(changed)

    if "\nimport git\n" in text:
        text = text.replace("\nimport git\n", "\n", 1)
        changes += 1

    text, changed = replace_once(
        text, 'if repo.endswith(".git"):', 'if repo.lower().endswith(".git"):'
    )
    changes += int(changed)

    old_clone = "git.Repo.clone_from(clone_url, repo_path, depth=1, single_branch=True)"
    new_clone = (
        "subprocess.run(\n"
        '                ["git", "clone", "--depth", "1", "--single-branch", clone_url, str(repo_path)],\n'
        "                check=True,\n"
        "                capture_output=True,\n"
        "                text=True,\n"
        "                timeout=90,\n"
        "                env={\n"
        '                    "GIT_TERMINAL_PROMPT": "0",\n'
        '                    "PATH": os.environ.get("PATH", ""),\n'
        "                },\n"
        "            )"
    )
    text, changed = replace_once(text, old_clone, new_clone)
    changes += int(changed)

    old_batch = (
        "        except typer.Exit as e:\n"
        "            if dry_run:\n"
        "                if e.exit_code == 0:\n"
        "                    success_count += 1\n"
        "                else:\n"
        "                    failure_count += 1\n"
        "                    failed_urls.append(url)\n"
        "                break  # dry-run exits after first URL\n"
        "            raise\n"
    )
    new_batch = (
        "        except typer.Exit as e:\n"
        "            if dry_run:\n"
        "                if e.exit_code == 0:\n"
        "                    success_count += 1\n"
        "                else:\n"
        "                    failure_count += 1\n"
        "                    failed_urls.append(url)\n"
        "                break  # dry-run exits after first URL\n"
        "            failure_count += 1\n"
        "            failed_urls.append(url)\n"
        '            console.print(f"[bold red]Error processing {url}:[/] exit code {e.exit_code}")\n'
        '            console.print("[yellow]Continuing to next URL...[/]")\n'
    )
    text, changed = replace_once(text, old_batch, new_batch)
    changes += int(changed)

    return text, changes


def patch_preflight(text: str) -> tuple[str, int]:
    changes = 0

    if "from typing import Optional\n" not in text:
        text, changed = replace_once(
            text,
            "from pathlib import Path\n",
            "from pathlib import Path\nfrom typing import Optional\n",
        )
        changes += int(changed)

    text, changed = replace_once(
        text,
        "def _is_valid_key_value(value: str | None) -> bool:",
        "def _is_valid_key_value(value: Optional[str]) -> bool:",
    )
    changes += int(changed)

    return text, changes


def apply(root: Path, write: bool) -> int:
    total_changes = 0

    cli_path = root / "pocarchitect" / "cli.py"
    preflight_path = root / "pocarchitect" / "preflight.py"
    ci_path = root / ".github" / "workflows" / "ci.yml"

    cli_text = read_text_with_fallback(cli_path)
    new_cli_text, cli_changes = patch_cli(cli_text)
    total_changes += cli_changes
    if write and cli_changes:
        cli_path.write_text(new_cli_text, encoding="utf-8")

    preflight_text = read_text_with_fallback(preflight_path)
    new_preflight_text, preflight_changes = patch_preflight(preflight_text)
    total_changes += preflight_changes
    if write and preflight_changes:
        preflight_path.write_text(new_preflight_text, encoding="utf-8")

    needs_ci = not ci_path.exists() or read_text_with_fallback(ci_path) != CI_YML
    if needs_ci:
        total_changes += 1
        if write:
            ci_path.parent.mkdir(parents=True, exist_ok=True)
            ci_path.write_text(CI_YML, encoding="utf-8")

    return total_changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply CI and compatibility fixes.")
    parser.add_argument(
        "--root", type=Path, default=Path.cwd(), help="Repository root path"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check whether fixes are needed without writing",
    )
    args = parser.parse_args()

    changes = apply(args.root, write=not args.check)
    if args.check:
        if changes:
            print(f"Needs patching: {changes} change(s) detected")
            return 1
        print("Already patched: no changes needed")
        return 0

    print(f"Applied patcher changes: {changes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
