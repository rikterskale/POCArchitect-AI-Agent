#!/usr/bin/env python3
"""Validate report structure and closure-evidence currentness, not behavior."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAP_REPORT = ROOT / "docs" / "DOCUMENTATION_GAP_ANALYSIS.md"
HISTORICAL_REPORT = ROOT / "docs" / "DOCUMENTATION_REVIEW_REPORT.md"
README = ROOT / "README.md"
QUICKSTART = ROOT / "POCArchitect_Quickstart.txt"
EXPECTED_IDS = {f"DOC-{number:03d}" for number in range(1, 29)}
HISTORICAL_COMMIT = "60d55d47c7ceb621df2f124764f01403a99f346b"
FINGERPRINT_PATTERN = re.compile(r"<!-- closure-evidence-sha256: ([0-9a-f]{64}) -->")
CITATION_PATTERN = re.compile(r"`([^`\n]+?):(\d+)(?:-(\d+))?`")


def closure_rows(text: str) -> dict[str, tuple[str, str]]:
    rows: dict[str, tuple[str, str]] = {}
    in_matrix = False
    for line in text.splitlines():
        if line.strip() == "## 10. Remediation closure matrix":
            in_matrix = True
            continue
        if in_matrix and line.startswith("## "):
            break
        if not in_matrix or not line.startswith("| DOC-"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 4:
            rows[cells[0]] = (cells[1], cells[2])
    return rows


def _normalized_file_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def evidence_fingerprint(root: Path, rows: dict[str, tuple[str, str]]) -> str:
    """Bind finding IDs and citation coordinates to normalized evidence bytes."""
    digest = hashlib.sha256()
    digest.update(b"documentation-closure-v2\0")
    paths: set[Path] = set()
    for finding_id in sorted(rows):
        status, evidence = rows[finding_id]
        digest.update(finding_id.strip().upper().encode("utf-8"))
        digest.update(b"\0")
        digest.update(status.strip().encode("utf-8"))
        digest.update(b"\0")
        citations = sorted(CITATION_PATTERN.findall(evidence))
        for raw_path, raw_start, raw_end in citations:
            relative = Path(raw_path)
            paths.add(relative)
            coordinate = (
                f"{relative.as_posix()}:{int(raw_start)}-{int(raw_end or raw_start)}"
            )
            digest.update(coordinate.encode("utf-8"))
            digest.update(b"\0")

    for relative in sorted(paths, key=lambda item: item.as_posix()):
        path = root / relative
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(_normalized_file_bytes(path)).digest())
        digest.update(b"\0")
    return digest.hexdigest()


def validate_citations(
    root: Path, rows: dict[str, tuple[str, str]]
) -> tuple[list[str], set[Path]]:
    errors: list[str] = []
    paths: set[Path] = set()
    for finding_id, (_, evidence) in rows.items():
        citations = CITATION_PATTERN.findall(evidence)
        if not citations:
            errors.append(f"{finding_id}: closure row has no path:line citation")
            continue
        for raw_path, raw_start, raw_end in citations:
            relative = Path(raw_path)
            paths.add(relative)
            path = root / relative
            if not path.is_file():
                errors.append(f"{finding_id}: cited path does not exist: {raw_path}")
                continue
            line_count = len(path.read_text(encoding="utf-8").splitlines())
            start = int(raw_start)
            end = int(raw_end or raw_start)
            if start < 1 or end < start or end > line_count:
                errors.append(
                    f"{finding_id}: citation {raw_path}:{start}-{end} is outside "
                    f"the current 1-{line_count} range"
                )
    return errors, paths


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    required = (GAP_REPORT, HISTORICAL_REPORT, README, QUICKSTART)
    for default_path in required:
        path = root / default_path.relative_to(ROOT)
        if not path.is_file():
            errors.append(f"Required documentation artifact is missing: {path}")
    if errors:
        return errors

    gap = (root / GAP_REPORT.relative_to(ROOT)).read_text(encoding="utf-8")
    historical = (root / HISTORICAL_REPORT.relative_to(ROOT)).read_text(
        encoding="utf-8"
    )
    readme = (root / README.relative_to(ROOT)).read_text(encoding="utf-8")
    quickstart = (root / QUICKSTART.relative_to(ROOT)).read_text(encoding="utf-8")

    if "structural controls do not prove behavioral accuracy" not in gap.lower():
        errors.append("Gap report must bound structural/currentness control claims")
    rows = closure_rows(gap)
    if set(rows) != EXPECTED_IDS:
        missing = sorted(EXPECTED_IDS - set(rows))
        extra = sorted(set(rows) - EXPECTED_IDS)
        errors.append(f"Closure matrix ID mismatch; missing={missing}, extra={extra}")
    for finding_id, (status, _) in rows.items():
        if status != "Closed":
            errors.append(f"{finding_id}: status must be Closed, found {status!r}")

    citation_errors, _ = validate_citations(root, rows)
    errors.extend(citation_errors)
    fingerprint_match = FINGERPRINT_PATTERN.search(gap)
    if fingerprint_match is None:
        errors.append("Gap report is missing closure evidence fingerprint")
    elif not citation_errors:
        current = evidence_fingerprint(root, rows)
        if fingerprint_match.group(1) != current:
            errors.append(
                "Closure evidence fingerprint is stale; recalculate current "
                "path:line evidence and fingerprint"
            )

    banner_prefix = (
        "> [!IMPORTANT]\n"
        "> **Historical snapshot — not current behavior or validation evidence.**"
    )
    if not historical.startswith("# Documentation Review Report\n\n" + banner_prefix):
        errors.append("Historical review report is missing the required top banner")
    if HISTORICAL_COMMIT not in historical:
        errors.append("Historical review report no longer identifies its commit")
    if "[Documentation Gap Analysis](DOCUMENTATION_GAP_ANALYSIS.md)" not in historical:
        errors.append("Historical review report does not link the current gap analysis")

    for target in (
        "docs/DOCUMENTATION_GAP_ANALYSIS.md",
        "docs/DOCUMENTATION_REVIEW_REPORT.md",
    ):
        if target not in readme:
            errors.append(f"README navigation is missing {target}")
    if "**historical snapshot**" not in readme:
        errors.append("README does not label the prior review as historical")

    if "docs/NOVICE_USABILITY_GUIDE.md" not in quickstart:
        errors.append("Root quickstart does not redirect to the canonical guide")
    if "--no-include-mitigations" in quickstart:
        errors.append("Root quickstart still advertises an unsupported option")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Documentation report validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(
        "Documentation report structure, current citation ranges, and evidence "
        "fingerprint are valid. Structural controls do not prove behavioral accuracy."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
