#!/usr/bin/env python3
"""Repair scripts/apply_ci_fixes.py if diff text was accidentally pasted into it."""

from __future__ import annotations

import subprocess
from pathlib import Path


TARGET = Path(__file__).resolve().parent / "apply_ci_fixes.py"
SHEBANG = "#!/usr/bin/env python3"


def repair_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")

    if not text.startswith("diff --git"):
        return False

    shebang_index = text.find(SHEBANG)
    if shebang_index == -1:
        restore_from_git(path)
        return True

    repaired = text[shebang_index:]
    path.write_text(repaired, encoding="utf-8")
    return True


def restore_from_git(path: Path) -> None:
    result = subprocess.run(
        ["git", "restore", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Detected diff contamination but could not auto-repair from shebang and "
            "`git restore` failed. Please run `git restore scripts/apply_ci_fixes.py` manually."
        )


def main() -> int:
    changed = repair_file(TARGET)
    if changed:
        print(f"Repaired: {TARGET}")
    else:
        print(f"No repair needed: {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
