import importlib.util
import io
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_distribution.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_distribution", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_member(archive, name: str, content: str) -> None:
    encoded = content.encode("utf-8")
    info = tarfile.TarInfo(name)
    info.size = len(encoded)
    archive.addfile(info, io.BytesIO(encoded))


def test_distribution_validator_checks_required_reports_and_links(tmp_path):
    validator = load_validator()
    archive_path = tmp_path / "pocarchitect-0.2.0.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        write_member(
            archive,
            "pocarchitect-0.2.0/README.md",
            "[Gap](docs/DOCUMENTATION_GAP_ANALYSIS.md)\n"
            "[History](docs/DOCUMENTATION_REVIEW_REPORT.md)\n",
        )
        write_member(
            archive,
            "pocarchitect-0.2.0/docs/DOCUMENTATION_GAP_ANALYSIS.md",
            "# Gap\n",
        )
        write_member(
            archive,
            "pocarchitect-0.2.0/docs/DOCUMENTATION_REVIEW_REPORT.md",
            "# History\n",
        )

    assert validator.validate_sdist(archive_path) == []


def test_distribution_validator_reports_missing_local_target(tmp_path):
    validator = load_validator()
    archive_path = tmp_path / "pocarchitect-0.2.0.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        write_member(
            archive,
            "pocarchitect-0.2.0/README.md",
            "[Missing](docs/missing.md)\n",
        )

    errors = validator.validate_sdist(archive_path)

    assert any("docs/missing.md" in error for error in errors)
