import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_docs.py"


def load_generator_module():
    spec = importlib.util.spec_from_file_location("generate_docs", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_reference_is_metadata_based_and_platform_neutral():
    generator = load_generator_module()

    first = generator.cli_reference()
    second = generator.cli_reference()

    assert first == second
    assert "reports/batch_progress.json" in first
    assert "terminal layout" in first
    assert "+- Options" not in first
    assert "xai \\| openai \\| groq \\| local" in first
    assert "--format json --no-color batch-status" in first
    assert "`<previous>`" in first
    assert "`<current>`" in first
    assert "`<sources>`" in first
    assert "`<report>`" in first


def test_configuration_reference_uses_runtime_defaults():
    generator = load_generator_module()

    reference = generator.config_reference()

    assert "| `groq` | `llama-3.1-70b-versatile` |" in reference
    assert "| `local` | `qwen2.5-coder:14b` |" in reference
    assert "imported from `pocarchitect/config.py`" in reference
    assert "when placed before the subcommand" in reference


def test_write_or_check_and_main_cover_write_current_and_stale_paths(
    tmp_path, monkeypatch, capsys
):
    generator = load_generator_module()
    target = tmp_path / "nested" / "generated.md"

    assert generator.write_or_check(target, "content\n", False) is True
    assert generator.write_or_check(target, "content\n", True) is True
    assert generator.write_or_check(target, "changed\n", True) is False

    monkeypatch.setattr(generator, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["generate_docs.py"])
    assert generator.main() == 0
    assert (tmp_path / "docs" / "cli-reference.md").is_file()
    assert (tmp_path / "docs" / "configuration-reference.md").is_file()

    monkeypatch.setattr(sys, "argv", ["generate_docs.py", "--check"])
    assert generator.main() == 0
    (tmp_path / "docs" / "cli-reference.md").write_text("stale", encoding="utf-8")
    assert generator.main() == 1
    assert "Generated documentation is stale" in capsys.readouterr().out
