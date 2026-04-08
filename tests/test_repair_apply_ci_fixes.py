from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

MODULE_PATH = (
    Path(__file__).resolve().parent.parent / "scripts" / "repair_apply_ci_fixes.py"
)
SPEC = spec_from_file_location("repair_apply_ci_fixes", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
repair_file = MODULE.repair_file


class CompletedProcessStub:
    def __init__(self, returncode: int):
        self.returncode = returncode


def test_repair_file_strips_leading_diff_blob(tmp_path: Path) -> None:
    target = tmp_path / "apply_ci_fixes.py"
    target.write_text(
        "diff --git a/scripts/apply_ci_fixes.py b/scripts/apply_ci_fixes.py\n"
        "index deadbeef..c0ffee 100644\n"
        "#!/usr/bin/env python3\n"
        "print('ok')\n",
        encoding="utf-8",
    )

    changed = repair_file(target)

    assert changed is True
    assert target.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3\n")


def test_repair_file_noop_for_clean_file(tmp_path: Path) -> None:
    target = tmp_path / "apply_ci_fixes.py"
    target.write_text("#!/usr/bin/env python3\nprint('ok')\n", encoding="utf-8")

    changed = repair_file(target)

    assert changed is False


def test_repair_file_falls_back_to_git_restore_when_shebang_missing(
    tmp_path: Path,
) -> None:
    target = tmp_path / "apply_ci_fixes.py"
    target.write_text(
        "diff --git a/scripts/apply_ci_fixes.py b/scripts/apply_ci_fixes.py\n",
        encoding="utf-8",
    )

    with patch.object(MODULE.subprocess, "run", return_value=CompletedProcessStub(0)):
        changed = repair_file(target)

    assert changed is True


def test_repair_file_reconstructs_when_text_is_raw_unified_diff(tmp_path: Path) -> None:
    target = tmp_path / "apply_ci_fixes.py"
    target.write_text(
        "\n".join(
            [
                "diff --git a/scripts/apply_ci_fixes.py b/scripts/apply_ci_fixes.py",
                "index 1111111..2222222 100644",
                "--- a/scripts/apply_ci_fixes.py",
                "+++ b/scripts/apply_ci_fixes.py",
                "@@ -1,1 +1,2 @@",
                "-print('old')",
                "+#!/usr/bin/env python3",
                "+print('ok')",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    changed = repair_file(target)

    assert changed is True
    assert target.read_text(encoding="utf-8") == "#!/usr/bin/env python3\nprint('ok')\n"


def test_repair_file_uses_template_when_other_repair_paths_still_contaminated(
    tmp_path: Path,
) -> None:
    target = tmp_path / "apply_ci_fixes.py"
    target.write_text("diff --git a/x b/y\n", encoding="utf-8")

    template = tmp_path / "apply_ci_fixes.template.py"
    template.write_text("#!/usr/bin/env python3\nprint('template')\n", encoding="utf-8")

    with (
        patch.object(MODULE, "TEMPLATE", template),
        patch.object(
            MODULE.subprocess, "run", return_value=SimpleNamespace(returncode=0)
        ),
    ):
        changed = repair_file(target)

    assert changed is True
    assert (
        target.read_text(encoding="utf-8")
        == "#!/usr/bin/env python3\nprint('template')\n"
    )
