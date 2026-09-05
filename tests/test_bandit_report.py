import json
import subprocess
import sys
from pathlib import Path

from scripts.validate_bandit_report import validate_report


def write_report(path: Path, *, errors=None, results=None) -> None:
    path.write_text(
        json.dumps({"errors": errors or [], "results": results or []}),
        encoding="utf-8",
    )


def test_bandit_report_accepts_only_a_complete_clean_scan(tmp_path):
    report = tmp_path / "bandit.json"
    write_report(report)
    assert validate_report(report) == []

    write_report(report, errors=[{"filename": "broken.py", "reason": "parse"}])
    assert "could not scan" in validate_report(report)[0]

    write_report(
        report,
        results=[
            {
                "filename": "unsafe.py",
                "line_number": 7,
                "test_id": "B999",
                "issue_severity": "HIGH",
            }
        ],
    )
    assert validate_report(report) == ["HIGH B999 at unsafe.py:7"]


def test_bandit_report_rejects_missing_and_malformed_reports(tmp_path):
    missing = tmp_path / "missing.json"
    assert "missing or invalid" in validate_report(missing)[0]

    malformed = tmp_path / "malformed.json"
    malformed.write_text("[]", encoding="utf-8")
    assert validate_report(malformed) == ["Bandit report root must be a JSON object"]

    malformed.write_text("{}", encoding="utf-8")
    assert "list-valued" in validate_report(malformed)[0]


def test_bandit_report_cli_returns_nonzero_for_scanner_errors(tmp_path):
    report = tmp_path / "bandit.json"
    write_report(report, errors=["could not parse file"])

    result = subprocess.run(
        [sys.executable, "scripts/validate_bandit_report.py", str(report)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "could not scan" in result.stdout
