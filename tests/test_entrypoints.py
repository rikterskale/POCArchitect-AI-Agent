import importlib.metadata
import runpy
from pathlib import Path


def test_only_packaged_cli_and_preflight_implementations_are_tracked():
    root = Path(__file__).resolve().parents[1]

    assert not (root / "cli.py").exists()
    assert not (root / "preflight.py").exists()
    assert (root / "pocarchitect" / "cli.py").exists()
    assert (root / "pocarchitect" / "preflight.py").exists()


def test_package_version_has_a_source_checkout_fallback(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(
        importlib.metadata,
        "version",
        lambda name: (_ for _ in ()).throw(
            importlib.metadata.PackageNotFoundError(name)
        ),
    )

    namespace = runpy.run_path(root / "pocarchitect" / "__init__.py")

    assert namespace["__version__"] == "0.2.0"
