import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_documentation_reports.py"


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "validate_documentation_reports", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_current_documentation_reports_pass_structural_currentness_controls():
    assert load_validator().validate(ROOT) == []


def test_validation_policy_distinguishes_current_manual_and_historical_evidence():
    policy = (ROOT / "docs" / "VALIDATION_CLAIMS.md").read_text(encoding="utf-8")

    for heading in (
        "## Evidence classes",
        "## Current claims",
        "## External or manual claims",
        "## Historical material",
    ):
        assert heading in policy
    assert "PyPI is not supported" in policy


def test_report_validator_rejects_out_of_range_closure_citation(tmp_path):
    validator = load_validator()
    evidence = tmp_path / "evidence.md"
    evidence.write_text("one line\n", encoding="utf-8")
    rows = {"DOC-001": ("Closed", "`evidence.md:2`")}

    errors, paths = validator.validate_citations(tmp_path, rows)

    assert paths == {Path("evidence.md")}
    assert any("outside" in error for error in errors)


def test_evidence_fingerprint_changes_with_cited_file(tmp_path):
    validator = load_validator()
    evidence = tmp_path / "evidence.md"
    evidence.write_text("first\n", encoding="utf-8")
    rows = {"DOC-001": ("Closed", "`evidence.md:1`")}
    before = validator.evidence_fingerprint(tmp_path, rows)

    evidence.write_text("second\n", encoding="utf-8")

    assert validator.evidence_fingerprint(tmp_path, rows) != before


def test_evidence_fingerprint_normalizes_lf_and_crlf(tmp_path):
    validator = load_validator()
    evidence = tmp_path / "evidence.md"
    rows = {"DOC-001": ("Closed", "`evidence.md:1-2`")}
    evidence.write_bytes(b"first\nsecond\n")
    lf_fingerprint = validator.evidence_fingerprint(tmp_path, rows)

    evidence.write_bytes(b"first\r\nsecond\r\n")

    assert validator.evidence_fingerprint(tmp_path, rows) == lf_fingerprint


def test_evidence_fingerprint_changes_when_only_citation_coordinates_change(
    tmp_path,
):
    validator = load_validator()
    evidence = tmp_path / "evidence.md"
    evidence.write_text("first\nsecond\n", encoding="utf-8")
    first_line = {"DOC-001": ("Closed", "`evidence.md:1`")}
    second_line = {"DOC-001": ("Closed", "`evidence.md:2`")}

    assert validator.evidence_fingerprint(
        tmp_path, first_line
    ) != validator.evidence_fingerprint(tmp_path, second_line)
