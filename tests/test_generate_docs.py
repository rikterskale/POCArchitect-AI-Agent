import importlib.util
from pathlib import Path

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
