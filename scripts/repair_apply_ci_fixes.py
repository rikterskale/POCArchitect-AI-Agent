#!/usr/bin/env python3
"""Repair scripts/apply_ci_fixes.py if diff text was accidentally pasted into it."""

from __future__ import annotations

import subprocess
from pathlib import Path


TARGET = Path(__file__).resolve().parent / "apply_ci_fixes.py"
TEMPLATE = Path(__file__).resolve().parent / "apply_ci_fixes.template.py"
SHEBANG = "#!/usr/bin/env python3"


def repair_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")

    if not is_contaminated(text):
        return False

    reconstructed = reconstruct_from_unified_diff(text)
    if reconstructed is not None:
        path.write_text(reconstructed, encoding="utf-8")
        return ensure_clean_or_restore_template(path)

    shebang_index = text.find(SHEBANG)
    if shebang_index != -1:
        repaired = text[shebang_index:]
        path.write_text(repaired, encoding="utf-8")
        return ensure_clean_or_restore_template(path)

    restore_from_git(path)
    return ensure_clean_or_restore_template(path)


def is_contaminated(text: str) -> bool:
    return text.startswith("diff --git")


def reconstruct_from_unified_diff(text: str) -> str | None:
    output_lines: list[str] = []
    in_hunk = False

    for line in text.splitlines():
        if line.startswith("@@ "):
            in_hunk = True
            continue
        if not in_hunk:
            continue
        if line.startswith("+++ ") or line.startswith("--- "):
            continue
        if line.startswith("+") and not line.startswith("+++"):
            output_lines.append(line[1:])
            continue
        if line.startswith(" "):
            output_lines.append(line[1:])

    if not output_lines:
        return None

    candidate = "\n".join(output_lines).lstrip("\n")
    if not candidate.startswith(SHEBANG):
        return None
    return candidate + ("\n" if not candidate.endswith("\n") else "")


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


def ensure_clean_or_restore_template(path: Path) -> bool:
    repaired_text = path.read_text(encoding="utf-8", errors="replace")
    if not is_contaminated(repaired_text):
        return True

    template_text = TEMPLATE.read_text(encoding="utf-8")
    path.write_text(template_text, encoding="utf-8")
    return True


def main() -> int:
    changed = repair_file(TARGET)
    if changed:
        print(f"Repaired: {TARGET}")
    else:
        print(f"No repair needed: {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
