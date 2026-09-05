# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-09-05

### Added

- Verified tag-driven GitHub release workflow with clean wheel/sdist installs,
  SHA-256 checksums, build provenance attestations, bounded job timeouts, and
  automated dependency updates for Python, Actions, and Docker.

- One-click credential-free GUI demo, automatic selection of an available cloud
  provider, in-place readiness refresh for newly added keys, current-session
  custom-output report discovery, persistent demo discovery, clearer source
  wording, and a GUI readability pass.
- Optional loopback-only web GUI with one-time transfer approval, structured
  progress streaming, source-file curation, and safe report browsing.
- Presentation-neutral prepare/execute analysis service and embedded event
  capture for non-terminal clients.
- Vendor-grade GUI design system with accessible tab semantics, responsive
  layouts, inline recovery states, selection-aware estimates, active-run
  recovery, report search and copy actions, and hardened local HTTP headers.
- Comprehensive GUI-first Start Here guide for novice users, including
  platform-specific installation, credential-free verification, provider
  setup, transfer approval, everyday workflows, and recovery instructions.
- Rich dashboard, grounding curation, per-phase timing, dry-run report previews, and post-run summary cards.
- Local and generic source inputs, project configuration scaffolding, report history/diffs, comparison, architecture diagrams, blueprint scaffolds, and HTML/PDF/JSON export.
- OSV dependency enrichment, analyzer entry points, example gallery, typo suggestions, guided doctor repairs, Gist publishing, a reusable GitHub Action, pre-commit hook, and scheduled analysis template.

- Hardened repository ingestion with bounded scans, symlink/special-file rejection,
  prompt-size limits, and fail-closed clone failures.
- Expanded secret redaction, atomic collision-safe report writes, locked batch
  ledgers, workflow schema validation, and a workflow CLI surface.
- Added security reporting guidance, package classifiers, static security CI,
  Docker health checks, and release distribution validation.

### Changed

- Replaced retired xAI and Groq defaults with `grok-4.6` and
  `openai/gpt-oss-120b`, including current input-cost estimates and alternatives.
- Included `SECURITY.md` in source distributions so packaged Start Here links
  resolve correctly.
- Made the credential-free CLI demo fully offline and socket-free, promoted
  Python 3.14 into the CI support matrix, and updated the security toolchain.
- The GUI now validates output-directory writability before source inspection
  or provider access, and the reusable Action rejects ambiguous boolean inputs.
- Updated the runtime and development dependency sets, GitHub Actions, and the
  Docker runtime to their validated current versions.
- Made release-readiness failures include bounded subprocess diagnostics and
  made clean-install platform simulation safe across supported Python versions.

### Security

- Credential updates, reports, history, diffs, and exports use atomic private
  writes with POSIX owner-only modes and Windows-compatible ACL behavior.
- GUI artifact access rejects files replaced by symlinks, and CI fails closed
  when Bandit reports an incomplete scan or any finding.

## [0.2.0]

Released as git tag `v0.2.0`. This is the earliest release with a recorded tag;
entries below the level of that tag are intentionally omitted because no prior
tagged history exists to verify them against.

[Unreleased]: https://github.com/rikterskale/POCArchitect-AI-Agent/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/rikterskale/POCArchitect-AI-Agent/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/rikterskale/POCArchitect-AI-Agent/releases/tag/v0.2.0
