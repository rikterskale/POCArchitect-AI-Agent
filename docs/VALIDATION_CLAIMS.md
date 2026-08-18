# Validation Claims and Evidence Policy

This page is the source of truth for interpreting validation language in this
repository. A passing structural check is not the same as a passing hosted run,
provider call, or platform installation.

## Evidence classes

| Class | Meaning | Where to verify |
|---|---|---|
| Current repository contract | Behavior or support policy encoded in the current source, tests, workflow, or docs. | Current `main` tree and the relevant CI job. |
| Locally reproducible | A maintainer can run the command from the checkout and reproduce the result without external credentials. | `python scripts/release_readiness.py`, validators, or targeted tests. |
| Hosted CI result | A GitHub Actions job passed for a specific commit. | The linked workflow run, not this repository page alone. |
| Manual external validation | A provider, Ollama service, Docker Desktop, WSL, or other external system was tested separately. | The release checklist and its recorded date/model/platform. |
| Historical snapshot | A result tied to an older commit or environment. It must not be used as current behavior evidence. | [`DOCUMENTATION_REVIEW_REPORT.md`](DOCUMENTATION_REVIEW_REPORT.md). |

## Current claims

The following are current repository claims and are enforced or checked by the
listed controls:

| Claim | Current control | Important boundary |
|---|---|---|
| Source checkout and release-artifact installation are supported | CI package and release-readiness jobs | PyPI is not supported. |
| Offline diagnosis and credential-free demo work | `doctor --offline`, `demo`, `quickstart`, and hermetic gate | Git is not required for these paths. |
| The packaged CLI exposes the documented commands/options | Generated-reference check and option inventory | This does not prove hosted CI success for a new commit. |
| Local-provider request routing and report writing work | Hermetic mock-provider gate | This does not prove a live provider or Ollama model works. |
| Linux, Windows, and macOS artifact first-install paths are intended support targets | Release-readiness matrix | The current hosted run must still be checked for the commit being released. |
| Docker image build, help, health, and report persistence are covered | Docker CI job | Native Docker Desktop behavior remains manual. |

## External or manual claims

These must be validated during the release checklist and must not be described
as proved by the offline gate:

- Real cloud-provider authentication, model availability, billing permissions,
  rate limits, and response handling.
- Live Ollama installation, model download, GPU/VRAM behavior, and generation.
- Interactive `setup` completion in a real terminal.
- WSL/Git Bash behavior.
- Native Docker Desktop bind mounts, path conversion, and TTY behavior.
- ARM64/Apple Silicon/Windows ARM host compatibility.

See the [manual external-provider checklist](RELEASE_READINESS.md#manual-release-checklist-for-external-providers).

## Historical material

[`DOCUMENTATION_REVIEW_REPORT.md`](DOCUMENTATION_REVIEW_REPORT.md) is a historical
snapshot tied to commit `60d55d47c7ceb621df2f124764f01403a99f346b`. Its command
results and limitations are not current validation evidence. Use the current
release-readiness gate, current workflow run, and current release checklist
instead.

## Reporting rule

Every release note, issue, or review that makes a readiness claim should name:

1. The commit or workflow run.
2. The command or job that produced the result.
3. The operating system and Python version where relevant.
4. Whether credentials, network, Docker, or external services were involved.
5. Whether the result is current, manual, or historical.
