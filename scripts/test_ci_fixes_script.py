from pathlib import Path


def test_apply_ci_fixes_script_is_valid_python_source() -> None:
    script_path = (
        Path(__file__).resolve().parent.parent / "scripts" / "apply_ci_fixes.py"
    )
    source = script_path.read_text(encoding="utf-8")

    assert source.startswith("#!/usr/bin/env python3\n")
    assert not source.startswith("diff --git")
    assert "\ndiff --git " not in source
