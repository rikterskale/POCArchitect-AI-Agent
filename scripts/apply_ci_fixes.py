diff --git a/scripts/apply_ci_fixes.py b/scripts/apply_ci_fixes.py
index 446dd1fd7e918d574902319f015e573bbcd41640..e8532cc50d3e1bd9bd43595afe4e0daee83f856b 100644
--- a/scripts/apply_ci_fixes.py
+++ b/scripts/apply_ci_fixes.py
@@ -143,69 +143,90 @@ def patch_cli(text: str) -> tuple[str, int]:
 
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
 
 
+def patch_pyproject(text: str) -> tuple[str, int]:
+    changes = 0
+    block = (
+        "\n[tool.black]\n"
+        'target-version = ["py39", "py310", "py311", "py312", "py313"]\n'
+    )
+
+    if "[tool.black]" not in text:
+        text = text.rstrip() + block + "\n"
+        changes += 1
+
+    return text, changes
+
+
 def apply(root: Path, write: bool) -> int:
     total_changes = 0
 
     cli_path = root / "pocarchitect" / "cli.py"
     preflight_path = root / "pocarchitect" / "preflight.py"
     ci_path = root / ".github" / "workflows" / "ci.yml"
+    pyproject_path = root / "pyproject.toml"
 
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
 
+    pyproject_text = read_text_with_fallback(pyproject_path)
+    new_pyproject_text, pyproject_changes = patch_pyproject(pyproject_text)
+    total_changes += pyproject_changes
+    if write and pyproject_changes:
+        pyproject_path.write_text(new_pyproject_text, encoding="utf-8")
+
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
