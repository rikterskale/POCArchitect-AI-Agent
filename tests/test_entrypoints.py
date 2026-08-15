from pathlib import Path


def test_only_packaged_cli_and_preflight_implementations_are_tracked():
    root = Path(__file__).resolve().parents[1]

    assert not (root / "cli.py").exists()
    assert not (root / "preflight.py").exists()
    assert (root / "pocarchitect" / "cli.py").exists()
    assert (root / "pocarchitect" / "preflight.py").exists()
