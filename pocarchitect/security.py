"""Bounded dependency extraction and OSV vulnerability enrichment."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

OSV_QUERY_URL = "https://api.osv.dev/v1/querybatch"


def extract_dependencies(text: str) -> list[dict[str, str]]:
    """Extract conservative package coordinates from common manifest snippets."""
    packages: set[tuple[str, str, str]] = set()
    for name, version in re.findall(
        r"(?m)^\s*([A-Za-z0-9_.-]+)\s*(?:==|~=|>=|<=)\s*([A-Za-z0-9_.+-]+)", text
    ):
        packages.add(("PyPI", name, version))
    # package.json-style exact versions only; ranges are intentionally omitted.
    for name, version in re.findall(
        r'"(@?[A-Za-z0-9_.\-/]+)"\s*:\s*"([0-9]+\.[0-9]+\.[0-9][A-Za-z0-9_.+-]*)"', text
    ):
        packages.add(("npm", name, version))
    for name, version in re.findall(
        r"(?m)^\s*([A-Za-z0-9_.-]+)\s*=\s*\{[^\n}]*version\s*=\s*\"([^\"]+)\"", text
    ):
        packages.add(("crates.io", name, version))
    return [
        {"ecosystem": ecosystem, "name": name, "version": version}
        for ecosystem, name, version in sorted(packages)[:100]
    ]


def query_osv(
    packages: list[dict[str, str]], timeout: float = 10.0
) -> list[dict[str, Any]]:
    """Query OSV's public batch API and return normalized vulnerability rows."""
    if not packages:
        return []
    payload = {
        "queries": [
            {
                "package": {"ecosystem": item["ecosystem"], "name": item["name"]},
                "version": item["version"],
            }
            for item in packages
        ]
    }
    request = Request(
        OSV_QUERY_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "pocarchitect/0.3"},
        method="POST",
    )
    with urlopen(
        request, timeout=timeout
    ) as response:  # nosec B310 - fixed HTTPS OSV endpoint
        result = json.loads(response.read().decode("utf-8"))
    findings: list[dict[str, Any]] = []
    for package, item in zip(packages, result.get("results", []), strict=False):
        for vulnerability in item.get("vulns", []):
            findings.append(
                {
                    **package,
                    "id": vulnerability.get("id"),
                    "aliases": vulnerability.get("aliases", []),
                    "summary": vulnerability.get("summary", ""),
                }
            )
    return findings


def scan_path(path: Path) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    chunks: list[str] = []
    names = {
        "requirements.txt",
        "pyproject.toml",
        "package.json",
        "package-lock.json",
        "cargo.toml",
    }
    for candidate in path.rglob("*"):
        if (
            candidate.is_file()
            and candidate.name.lower() in names
            and candidate.stat().st_size <= 1_000_000
        ):
            chunks.append(candidate.read_text(encoding="utf-8", errors="ignore"))
    packages = extract_dependencies("\n".join(chunks))
    return packages, query_osv(packages)
