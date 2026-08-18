# POCArchitect Documentation Gap Analysis

> [!NOTE]
> **Baseline audit plus current remediation record.** Sections 1-9 and
> Appendices A-C preserve the complete pre-remediation audit performed against
> commit `0c45740521c6f92b85247451c9ad54c77231a2b9` on 2026-08-15. Their
> `path:line` citations intentionally identify that baseline snapshot. Section
> 10 is the authoritative current-tree closure matrix; its citations and
> evidence fingerprint are recalculated after remediation. The CI controls
> validate structure, local targets, citation ranges, normalized evidence-file
> content, and the finding-to-coordinate mapping. Structural controls do not prove behavioral accuracy;
> executable behavior is established by the separately listed tests and checks.

**Repository audited:** `C:\Users\tsaxon\Documents\Github\POCArchitect-AI-Agent`
**Baseline audit commit:** `0c45740521c6f92b85247451c9ad54c77231a2b9`
**Current-tree audit date:** 2026-08-15
**Scope authority:** `git ls-files`
**Report basis:** direct baseline working-tree text evidence unless a row is explicitly labeled **Command result** or **Not determinable**.

## 1. Scope and methodology

### 1.1 Authoritative scope and full-read procedure

A NUL-delimited `git ls-files -z` enumeration returned **54 tracked files**. A byte-level pass then opened every listed path, iterated every line, and recorded **6,672 lines**, **257,116 bytes**, zero missing paths, and zero NUL-containing files. The coverage ledger in Appendix A is generated from that same list. Its set was independently compared with a fresh `git ls-files -z` result: **exact match; 54 expected, 54 ledger rows, 0 missing, 0 extra**.

`review-output/` exists locally, but `git ls-files -- review-output review-output/**` returned no paths and `git check-ignore -v review-output` identified `.gitignore:25`; the tracked ignore rule is explicit at `.gitignore:24-25`. Therefore no file under `review-output/` entered the line-by-line scope and none was used as evidence.

Every tracked file was read completely, including both top-level and packaged Python implementations, tests, shell scripts, CI, generated references, examples, metadata, prompt text, and the prior review report. The prior report identifies its own reviewed commit and environment at `docs/DOCUMENTATION_REVIEW_REPORT.md:18-27`; it was treated only as a historical tracked artifact, never as ground truth. Each finding below was independently checked against baseline files.

### 1.2 Evidence rules

- **Direct evidence** means an exact baseline `path:line` or `path:start-end` citation. Findings do not assume provider, Docker, operating-system, or network behavior that is absent from repository text.
- **Absence findings** cite the implemented/configured surface and the closest relevant documentation locations that were exhaustively read. The statement is limited to what those locations omit or contradict.
- **Command results** are separated from static evidence. No command result is used to invent runtime behavior beyond what was exercised.
- **Not determinable** items are collected in Appendix B rather than converted into findings.
- Severity is audit prioritization: **Critical** = documentation can directly cause an unrecoverable or safety-critical outcome; **High** = materially wrong operational, automation, provenance, or maintenance guidance; **Medium** = workflow-affecting omission or contradiction with a bounded workaround; **Low** = discoverability, precision, traceability, or maintainability debt.

### 1.3 Read-only command results

| Command/probe | Baseline result | Evidentiary use |
|---|---|---|
| `git rev-parse HEAD`; `git branch --show-current` | `0c45740521c6f92b85247451c9ad54c77231a2b9`, branch `main` | Identifies the working tree audited; not a substitute for file citations. |
| `git status --short --untracked-files=all` | No output before analysis | Confirms the repository began clean. |
| `python scripts/validate_novice_guides.py` | Passed: “Novice guides are complete and command-ledger validated.” | Establishes only that the checks coded at `scripts/validate_novice_guides.py:35-90` passed. |
| `python scripts/validate_documentation_links.py` | Passed: 15 Markdown files | Establishes only the local-link checks coded at `scripts/validate_documentation_links.py:20-71`; external URLs are explicitly skipped at `scripts/validate_documentation_links.py:46-49`. |
| `python scripts/generate_docs.py --check` | Not run to completion: import failed because `openai` was not installed | No generated-document freshness claim is made from this environment. The import dependency follows from `scripts/generate_docs.py:62-65` and `pocarchitect/cli.py:15-17`. No dependency was installed. |
| `python scripts/apply_ci_fixes.py --check` | Exit 1, “Needs patching: 1 change(s) detected” | Corroborates the literal workflow drift in DOC-016; static text remains primary evidence. |
| Isolated `CliRunner` probe, `--format json batch-status` / `batch-reset` | Both emitted one JSON object and exited 0 | Corroborates DOC-003. Missing imports were stubbed; no provider or filesystem state was exercised. |
| Isolated one-item batch probe with a forced item exception | Summary reported `failed=1`; command exit was 0 | Corroborates DOC-008. Preflight/provider work was stubbed solely to force the documented control path. |

No provider request, live Ollama request, Docker build, package build, or dependency installation was performed. The two repository documentation validators were useful and read-only. The full test suite was not run because the environment lacked declared runtime imports; this report does not repeat the historical pass claims at `docs/DOCUMENTATION_REVIEW_REPORT.md:115-129` as current results.

## 2. Executive summary

The baseline tree had **28 evidence-supported documentation findings**: **0 Critical, 9 High, 13 Medium, and 6 Low**.

### 2.1 Counts by severity

| Severity | Count | Finding IDs |
|---|---:|---|
| Critical | 0 | — |
| High | 9 | DOC-001, DOC-002, DOC-003, DOC-004, DOC-006, DOC-008, DOC-012, DOC-015, DOC-016 |
| Medium | 13 | DOC-005, DOC-007, DOC-009, DOC-011, DOC-013, DOC-014, DOC-017, DOC-018, DOC-019, DOC-020, DOC-021, DOC-022, DOC-024 |
| Low | 6 | DOC-010, DOC-023, DOC-025, DOC-026, DOC-027, DOC-028 |
| **Total** | **28** | — |

### 2.2 Counts by gap category

| Category | Count | Finding IDs |
|---|---:|---|
| Architecture / entry points | 1 | DOC-001 |
| CLI reference / command syntax | 2 | DOC-002, DOC-003 |
| Preflight / configuration | 4 | DOC-004, DOC-005, DOC-021, DOC-024 |
| Grounding / transfer | 2 | DOC-006, DOC-007 |
| Batch / state | 4 | DOC-008, DOC-009, DOC-010, DOC-011 |
| Outputs / packaging / links | 2 | DOC-012, DOC-013 |
| Docker | 1 | DOC-014 |
| Scripts / CI | 3 | DOC-015, DOC-016, DOC-018 |
| Documentation tooling / validation | 2 | DOC-017, DOC-019 |
| Platform instructions | 1 | DOC-020 |
| Examples | 1 | DOC-022 |
| Providers / models | 1 | DOC-023 |
| Tests / test configuration | 1 | DOC-025 |
| Duplication / maintainability | 1 | DOC-026 |
| Historical documentation | 1 | DOC-027 |
| Local-provider helper | 1 | DOC-028 |

### 2.3 Highest-priority conclusions

The most consequential baseline gaps were directly evidenced: the repository carried two divergent CLI/preflight implementations while packaging selected only one (DOC-001); the root quickstart contradicted the public option declarations (DOC-002); batch JSON output was implemented while multiple references said it was unavailable (DOC-003); automatic preflight did not use `--output-dir` or `IN_DOCKER` even though troubleshooting pointed users to those settings (DOC-004); clone failures fell through to provider processing without that fallback being documented (DOC-006); per-item batch failures could still leave the command with a zero exit (DOC-008); report provenance could say `github-shallow-clone` when no clone occurred (DOC-012); the verification scripts selected the wrong preflight mode/provider (DOC-015); and the CI patch/repair scripts contained workflow definitions that conflicted with the checked-in workflow (DOC-016). The supporting citations appear in each finding and are not taken from the prior review report.

## 3. Documentation-source inventory

This inventory includes files whose primary purpose is user guidance, reference, examples, policy, or an operator-facing helper/template. Build/test/config files are inventoried separately in the capability matrix and complete ledger.

| Artifact | Explicit purpose/content | Evidence |
|---|---|---|
| `.env.example` | Cloud-provider credential template with intentionally rejected placeholders. | `.env.example:1-14` |
| `LICENSE` | MIT permission, conditions, and warranty disclaimer. | `LICENSE:3-22` |
| `POCArchitect_Quickstart.txt` | Beginner installation, setup, Docker, usage, flags, report location, and troubleshooting page. | `POCArchitect_Quickstart.txt:1-24`, `POCArchitect_Quickstart.txt:73-126` |
| `README.md` | Repository landing page: behavior boundary, features, safe start, platform matrix, common options, navigation, authorization, support, and license. | `README.md:1-17`, `README.md:18-46`, `README.md:48-105` |
| `docs/DOCUMENTATION_REVIEW_REPORT.md` | Snapshot-style prior documentation review, validation claims, traceability, unresolved issues, scorecard, and recommendations. | `docs/DOCUMENTATION_REVIEW_REPORT.md:1-27`, `docs/DOCUMENTATION_REVIEW_REPORT.md:115-193` |
| `docs/NOVICE_USABILITY_GUIDE.md` | Canonical novice journey from prerequisites through installation, safe run, troubleshooting, operations, cleanup, support, and glossary. | `docs/NOVICE_USABILITY_GUIDE.md:1-17`, `docs/NOVICE_USABILITY_GUIDE.md:92-199`, `docs/NOVICE_USABILITY_GUIDE.md:201-310` |
| `docs/POCArchitect_Example_Report.md` | Prominently labeled static, non-functional report-format example with illustrative report sections and code. | `docs/POCArchitect_Example_Report.md:1-15`, `docs/POCArchitect_Example_Report.md:212-311` |
| `docs/agentusage.md` | Short CLI orientation, option table, safe preview, batch example, dry-run notes, and links to canonical references. | `docs/agentusage.md:1-25`, `docs/agentusage.md:27-81` |
| `docs/architecture.md` | Implementation-oriented flow, components, limits, dependencies, and boundaries. | `docs/architecture.md:1-15`, `docs/architecture.md:18-81` |
| `docs/cli-reference.md` | Generated main-command/subcommand option tables and safe examples. | `docs/cli-reference.md:1-5`, `docs/cli-reference.md:9-73` |
| `docs/command-guide.md` | End-to-end installation, providers, single/batch/automation/Docker/development commands, and troubleshooting. | `docs/command-guide.md:1-18`, `docs/command-guide.md:20-373` |
| `docs/configuration-reference.md` | Credential, environment, command-setting, default, sensitivity, and source-location tables. | `docs/configuration-reference.md:1-43` |
| `docs/docker-guide.md` | Docker prerequisites, build/run patterns, secrets, mounts, batch use, alias, and troubleshooting. | `docs/docker-guide.md:1-20`, `docs/docker-guide.md:24-134` |
| `docs/guides/LINUX_NOVICE_USABILITY_GUIDE.md` | Bash/Linux supplement and command ledger linked to the canonical guide. | `docs/guides/LINUX_NOVICE_USABILITY_GUIDE.md:1-21`, `docs/guides/LINUX_NOVICE_USABILITY_GUIDE.md:23-166` |
| `docs/guides/WINDOWS_NOVICE_USABILITY_GUIDE.md` | Windows PowerShell supplement and command ledger linked to the canonical guide. | `docs/guides/WINDOWS_NOVICE_USABILITY_GUIDE.md:1-21`, `docs/guides/WINDOWS_NOVICE_USABILITY_GUIDE.md:23-166` |
| `docs/ollama-setup-guide.md` | Ollama installation, server/model setup, helper use, CLI use, limitations, and troubleshooting for `local`. | `docs/ollama-setup-guide.md:1-10`, `docs/ollama-setup-guide.md:11-81` |
| `docs/ollama_preflight_check.py` | Operator-facing helper that checks Ollama version, one model, and one chat-completions request and prints readiness panels. | `docs/ollama_preflight_check.py:1-16`, `docs/ollama_preflight_check.py:24-130` |
| `example_usage/batch_urls.txt` | Two example batch URL values. | `example_usage/batch_urls.txt:1-2` |
| `example_usage/single_url_example.md` | One bare illustrative URL. | `example_usage/single_url_example.md:1` |
| `example_usage/usage.md` | Two safe no-ingest dry-run command examples. | `example_usage/usage.md:1-11` |
| `pocarchitect/POC_Architect_Prompt.md` | Packaged provider system prompt defining identity, input contract, analysis pipeline, output requirements, and report content. | `pocarchitect/POC_Architect_Prompt.md:1-36`, `pocarchitect/POC_Architect_Prompt.md:40-137` |
| `verify.sh` | Bash dry-run verification script with installation, help, preflight, single, option, and batch checks. | `verify.sh:1-12`, `verify.sh:14-72` |
| `test-full.sh` | Bash real-provider test script that warns about credits and runs OpenAI single/option/batch workflows. | `test-full.sh:1-16`, `test-full.sh:18-70` |

## 4. Documented-vs-implemented capability matrix

| Surface | Direct implementation/config/test evidence | Relevant documentation evidence | Assessment |
|---|---|---|---|
| CLI entry points | Console entry point is `pocarchitect.cli:app`; module entry imports the same app. `pyproject.toml:23-24`; `pocarchitect/__main__.py:2-9`. Separate tracked root scripts also define a CLI/preflight. `cli.py:47-50`; `cli.py:464-564`; `preflight.py:14-21`. | Supported forms are `pocarchitect` and `python -m pocarchitect`. `docs/command-guide.md:65-87`; architecture points to `pocarchitect/cli.py`. `docs/architecture.md:37-44`. | Public packaged path is documented, but the root duplicates have no status/explanation: DOC-001. |
| Main CLI commands/options | Main options are declared at `pocarchitect/cli.py:785-855`; subcommands at `pocarchitect/cli.py:81-109` and `pocarchitect/cli.py:717-782`. | Generated table covers all declared main/subcommand options. `docs/cli-reference.md:9-65`. | Canonical table is broad, but the root quickstart conflicts and batch-global formatting is misdescribed: DOC-002, DOC-003. |
| Defaults | Provider models are `grok-3`, `gpt-4o`, `llama-3.1-70b-versatile`, and `qwen2.5-coder:32b`; temperature is `0.2`; labels are `High`/`Linux`. `pocarchitect/cli.py:72-78`; `pocarchitect/cli.py:797-824`. | Effective option defaults are spread across README/reference/architecture. `README.md:54-70`; `docs/architecture.md:50-56`. | Main defaults are mostly documented; the complete model map and prompt compatibility boundary are not: DOC-023. |
| Configuration/environment | Cloud keys are mapped by provider; local default is `http://localhost:11434/v1`; output also recognizes `IN_DOCKER`. `pocarchitect/preflight.py:21-30`; `pocarchitect/cli.py:128-131`; `pocarchitect/cli.py:443-468`. | Credential/settings table lists the keys, `IN_DOCKER`, endpoint, and precedence. `docs/configuration-reference.md:5-39`. | Key names and effective settings are covered; preflight/output interactions and local-key wording conflict: DOC-004, DOC-021, DOC-024. |
| Outputs/artifacts | Reports contain front matter with seven fields and a body SHA-256, then provider text. `pocarchitect/cli.py:134-165`. JSON events always start with `event` and `message`. `pocarchitect/output.py:1-10`; `pocarchitect/cli.py:52-69`. | Docs state report path/name, metadata/body hash, and JSON Lines basics. `docs/NOVICE_USABILITY_GUIDE.md:176-186`; `docs/NOVICE_USABILITY_GUIDE.md:229-237`. | Broadly covered, but exact schema/provenance edge cases are not: DOC-003, DOC-012. |
| Preflight checks | Checks Python, five imports, CLI help, prompt, provider readiness when requested, and default output path. `pocarchitect/preflight.py:30`; `pocarchitect/preflight.py:87-126`; `pocarchitect/preflight.py:129-229`. | README and novice guide describe offline checks. `README.md:30-37`; `docs/NOVICE_USABILITY_GUIDE.md:180-199`. | Check list is partially described; automatic dry-run/output behavior, Git omission, and local endpoint scope need correction: DOC-004, DOC-005, DOC-024. |
| Grounding and transfer | GitHub clone is depth-one, noninteractive, 90 seconds; selection uses filename keywords/extensions, 250,000-byte skip, 7,500-character truncation, first 25; exceptions become warning context. `pocarchitect/cli.py:286-425`. Transfer text is redacted and confirmed. `pocarchitect/cli.py:168-238`. | Architecture states clone, confirmation, 25-file and 7,500-character limits. `docs/architecture.md:5-14`; `docs/architecture.md:72-77`. | Core boundary is documented; failure fallback and complete selection rules are not: DOC-006, DOC-007. |
| State/resume | Versioned JSON state is loaded/written atomically and reset to a backup. `pocarchitect/state.py:12-84`. Batch records success/failure and skips successful URLs. `pocarchitect/cli.py:608-713`. | README and guides cover default path, skip/retry, status, reset, and backup. `README.md:48-50`; `docs/command-guide.md:214-248`. | Recovery concept is covered; exit semantics, dry-run scope, input grammar, and JSON schema are incomplete: DOC-008 through DOC-011. |
| Packaging/entry data | Python `>=3.10`, console script, package discovery, and Markdown package data are declared. `pyproject.toml:1-24`; `pyproject.toml:31-38`. The sdist manifest includes README but prunes docs/examples. `MANIFEST.in:3-21`. | Installation and both invocation forms are documented. `README.md:30-37`; `docs/command-guide.md:20-87`. | Entry forms are covered; distribution navigation is inconsistent: DOC-001, DOC-013. |
| Docker | Multi-stage Python 3.12 image installs Git, creates/chowns `/reports`, runs as `pocuser`, and uses the CLI as entry point. `Dockerfile:1-33`. CI builds and runs `--help`. `.github/workflows/ci.yml:125-136`. | Docker guide covers build, safe/interactive/batch runs and writable mounts. `docs/docker-guide.md:14-93`; `docs/docker-guide.md:109-134`. | Main path is documented; the advertised alias cannot satisfy the documented interactive confirmation path: DOC-014. |
| Scripts | Generator, two validators, CI patcher/template/repair, dry-run verifier, and real-call test are all tracked. `scripts/generate_docs.py:1-168`; `scripts/validate_documentation_links.py:1-76`; `scripts/validate_novice_guides.py:1-95`; `scripts/apply_ci_fixes.py:1-204`; `scripts/repair_apply_ci_fixes.py:1-100`; `verify.sh:1-72`; `test-full.sh:1-70`. | Command guide documents generator and the two shell scripts, but not the patch/repair or validators. `docs/command-guide.md:322-356`. | Material script behavior and safeguards are incomplete or wrong: DOC-015 through DOC-019. |
| CI | Quality, test matrix, security, Docker, and package-build jobs are explicit. `.github/workflows/ci.yml:16-160`. | README mentions Ubuntu versions and Docker smoke; command guide lists a subset of local checks. `README.md:39-46`; `docs/command-guide.md:322-356`. | Platform summary is supported, but contributor reproduction is incomplete: DOC-016, DOC-018, DOC-019. |
| Tests | There are 32 statically declared test functions across eight tracked test modules; their asserted surfaces are visible in `tests/test_cli.py:16-311`, `tests/test_preflight.py:7-133`, and the six smaller test files in Appendix A. Pytest metadata declares markers. `pytest.ini:1-26`. | Prior report records a historical 32-test pass. `docs/DOCUMENTATION_REVIEW_REPORT.md:115-126`; command guide says `pytest`. `docs/command-guide.md:330-338`. | Test inventory is visible, but current pass status was not established and the slow-marker description conflicts with invocation config: DOC-025; current pass status is Not Determinable. |
| Examples | Safe examples use `--no-ingest --dry-run`; batch and single URL files contain illustrative values. `example_usage/usage.md:1-11`; `example_usage/batch_urls.txt:1-2`; `example_usage/single_url_example.md:1`. | Quickstart and real-call script consume the batch file. `POCArchitect_Quickstart.txt:97-102`; `test-full.sh:51-56`. | Safe command examples are clear; real-call use of unlabeled placeholder URLs is not: DOC-022. |
| Platform instructions | CI uses Ubuntu/Python 3.10-3.13. `.github/workflows/ci.yml:60-96`. Packaging checks Python version only. `pyproject.toml:6`; `pocarchitect/preflight.py:155-160`. | README matrix, canonical guide, and platform supplements state validation limits and commands. `README.md:39-46`; `docs/NOVICE_USABILITY_GUIDE.md:35-40`; `docs/guides/WINDOWS_NOVICE_USABILITY_GUIDE.md:54-56`; `docs/guides/LINUX_NOVICE_USABILITY_GUIDE.md:54-56`. | Commands exist for Windows/Linux/macOS, but support/evidence wording is incomplete or unsupported: DOC-020. |

## 5. Detailed findings

### DOC-001 — Two divergent CLI/preflight implementations have no documented status

- **Severity:** High
- **Category:** Architecture / entry points
- **Documentation evidence:** Architecture names `pocarchitect/cli.py` as orchestration but names bare `cli.py` for report saving (`docs/architecture.md:37-44`). User commands document only the installed script and module forms (`docs/command-guide.md:65-87`).
- **Implementation/config/test evidence:** Packaging selects `pocarchitect.cli:app` (`pyproject.toml:23-24`) and `python -m` imports that app (`pocarchitect/__main__.py:2-9`). Nevertheless, tracked root `cli.py` declares a separate app and preflight wrapper (`cli.py:23-50`), a smaller option set (`cli.py:464-499`), and a different report writer without packaged metadata (`cli.py:75-84`); packaged code has state commands/global formatting and metadata (`pocarchitect/cli.py:134-165`, `pocarchitect/cli.py:717-855`). Root `preflight.py` also declares a different dependency list and behavior (`preflight.py:14-21`, `preflight.py:100-157`) from `pocarchitect/preflight.py:21-30` and `pocarchitect/preflight.py:129-229`.
- **Observed mismatch/omission:** The supported packaged entry point is explicit, but no tracked documentation explains the purpose, support status, or non-equivalence of the two root implementations. The architecture's bare `cli.py` path is ambiguous precisely because both paths exist.
- **Affected audience/workflow:** Users trying `python cli.py`, maintainers editing the wrong implementation, reviewers tracing behavior, and release engineers.
- **Concrete documentation correction:** Add an architecture/maintainer note that identifies the authoritative runtime path selected by `pyproject.toml`, lists the root copies, and states their intended support status only after a maintainer decision. Change the report-saving path to `pocarchitect/cli.py` if that is the intended component.

### DOC-002 — The root quickstart contradicts the public option surface and contains split commands

- **Severity:** High
- **Category:** CLI reference / command syntax
- **Documentation evidence:** The quickstart presents Docker and single-URL commands over separate lines without continuation markers (`POCArchitect_Quickstart.txt:67-88`) and lists `--risk-level Critical|High|Medium|Low`, fixed target-OS values, and `--no-include-mitigations` (`POCArchitect_Quickstart.txt:103-112`). Canonical references instead say risk/target are free text and no public disable switch exists (`README.md:61-64`; `docs/cli-reference.md:18-21`).
- **Implementation/config/test evidence:** The public declarations accept strings for risk/target and declare only `--include-mitigations` plus `--no-ingest` (`pocarchitect/cli.py:812-826`).
- **Observed mismatch/omission:** One root-level beginner document advertises a switch absent from the declaration, describes free-text inputs as enumerations, and formats multi-line invocations differently from valid continued examples such as `docs/command-guide.md:292-317`.
- **Affected audience/workflow:** First-time local and Docker users copying commands.
- **Concrete documentation correction:** Replace the quickstart with a short redirect to `docs/NOVICE_USABILITY_GUIDE.md`, or regenerate every command from the canonical option table; remove the negative mitigation switch, label risk/target as free text, and use fenced one-line or correctly continued commands.

### DOC-003 — Batch subcommand JSON support is implemented but documentation says it is unavailable

- **Severity:** High
- **Category:** CLI reference / command syntax
- **Documentation evidence:** The CLI reference calls `batch-status` “machine-readable” (`docs/cli-reference.md:42-45`), while the configuration reference says both batch subcommands are human-readable and “not JSON Lines” (`docs/configuration-reference.md:41-43`). The novice and command guides repeat the latter restriction (`docs/NOVICE_USABILITY_GUIDE.md:229-233`; `docs/command-guide.md:250-259`).
- **Implementation/config/test evidence:** `--format` and `--no-color` are root callback options (`pocarchitect/cli.py:847-852`); output is configured before returning to the selected subcommand (`pocarchitect/cli.py:857-859`); both batch subcommands use `emit` (`pocarchitect/cli.py:717-782`), whose JSON branch emits an event object (`pocarchitect/cli.py:59-69`). The isolated command probe confirmed `pocarchitect --format json batch-status ...` and `batch-reset ...` each emitted JSON.
- **Observed mismatch/omission:** The documents contradict one another and omit the required placement of global formatting options before the subcommand name.
- **Affected audience/workflow:** CI, shell integrations, state-monitoring tools, and screen-reader/no-color users.
- **Concrete documentation correction:** Document `pocarchitect --format json --no-color batch-status --batch-state <path>` and the equivalent reset form, describe their event fields from `emit`, and remove the statements that JSON Lines is limited to the main command and preflight.

### DOC-004 — `--output-dir` and `IN_DOCKER` do not control the automatic preflight output check

- **Severity:** High
- **Category:** Preflight / configuration
- **Documentation evidence:** The configuration reference says `IN_DOCKER` selects `/reports` and `--output-dir` selects a writable report destination (`docs/configuration-reference.md:17`, `docs/configuration-reference.md:30-32`). Troubleshooting tells a user with an output permission error to choose a directory with `--output-dir` (`docs/NOVICE_USABILITY_GUIDE.md:197-199`; see also `docs/guides/WINDOWS_NOVICE_USABILITY_GUIDE.md:82-84`).
- **Implementation/config/test evidence:** A real main run calls preflight before resolving `output_dir` (`pocarchitect/cli.py:867-884`) and does not pass that option to preflight (`pocarchitect/cli.py:869-875`). The preflight check chooses only `/reports` when `/.dockerenv` exists, otherwise `cwd/reports`; it does not inspect `IN_DOCKER` or a caller path (`pocarchitect/preflight.py:98-112`). The main report default separately recognizes both `/.dockerenv` and `IN_DOCKER` (`pocarchitect/cli.py:128-131`).
- **Observed mismatch/omission:** The documented remedy/configuration affects report saving but cannot change the path tested by the automatic preflight. A real run can therefore fail its default-directory check before reaching a separately writable `--output-dir`.
- **Affected audience/workflow:** Users in read-only working directories, container wrappers using `IN_DOCKER`, and automation selecting an external report directory.
- **Concrete documentation correction:** State exactly which path automatic/offline preflight tests, state that the current preflight has no `--output-dir` input and ignores `IN_DOCKER`, and do not present `--output-dir` as a remedy for that preflight failure unless implementation is changed.

### DOC-005 — Dry-run documentation understates the preflight bypass

- **Severity:** Medium
- **Category:** Preflight / configuration
- **Documentation evidence:** README says dry run “skips provider readiness checks” (`README.md:11-16`); architecture likewise says it skips the “provider-readiness preflight” (`docs/architecture.md:9-14`).
- **Implementation/config/test evidence:** The main callback executes `run_preflight(...)` only when `not dry_run` (`pocarchitect/cli.py:867-875`). That skipped function contains Python, dependency, CLI, prompt, provider, and output-directory checks (`pocarchitect/preflight.py:155-198`).
- **Observed mismatch/omission:** The current code bypasses the entire automatic preflight, not only provider readiness.
- **Affected audience/workflow:** Users treating a successful dry run as installation/output-path validation.
- **Concrete documentation correction:** Replace the narrower wording with “`--dry-run` bypasses automatic preflight entirely”; point users who need installation checks to the separately documented `preflight --offline` command (`README.md:30-37`).

### DOC-006 — Clone failures degrade to warning-only grounding and can proceed to a provider

- **Severity:** High
- **Category:** Grounding / transfer
- **Documentation evidence:** Troubleshooting says to correct a failed clone or use a safe no-ingest dry run (`docs/command-guide.md:358-370`; `docs/NOVICE_USABILITY_GUIDE.md:271-274`). Architecture describes non-GitHub URL-only grounding but does not describe a GitHub clone-failure fallback (`docs/architecture.md:5-14`).
- **Implementation/config/test evidence:** `build_grounding_context` catches every exception, appends `WARNING: Ingestion failed (...)`, and returns that context (`pocarchitect/cli.py:423-425`). `process_single_url` then confirms the returned text on a real ingestion path and proceeds to `get_llm_response` and `save_report` without checking whether cloning succeeded (`pocarchitect/cli.py:508-562`).
- **Observed mismatch/omission:** Relevant docs explain diagnosis but omit that a real GitHub run can continue after clone failure with warning/URL context and still reach a billable provider call after confirmation.
- **Affected audience/workflow:** Operators expecting grounded analysis, reviewers relying on source-backed reports, and cost-sensitive provider users.
- **Concrete documentation correction:** In architecture, command, and troubleshooting guides, describe the exact warning fallback and instruct operators to inspect the preview for `WARNING: Ingestion failed` before approving transfer; avoid calling such a run grounded.

### DOC-007 — Grounding-selection documentation omits material selection rules

- **Severity:** Medium
- **Category:** Grounding / transfer
- **Documentation evidence:** Architecture documents “at most 25 matching files” and 7,500-character per-file truncation (`docs/architecture.md:72-76`), while the novice guide only says selection is bounded (`docs/NOVICE_USABILITY_GUIDE.md:275-277`).
- **Implementation/config/test evidence:** Selection uses a fixed keyword list (`pocarchitect/cli.py:337-358`), a fixed extension set (`pocarchitect/cli.py:359-374`), silently skips files over 250,000 bytes (`pocarchitect/cli.py:376-387`), truncates selected content at 7,500 characters (`pocarchitect/cli.py:394-400`), and emits only `critical[:25]` (`pocarchitect/cli.py:404-415`).
- **Observed mismatch/omission:** The documented limits omit the 250,000-byte exclusion and the criteria that determine which files can enter the first 25.
- **Affected audience/workflow:** Operators assessing source coverage and maintainers diagnosing omitted files.
- **Concrete documentation correction:** Add a current selection-rules table with the exact keywords, extensions, byte threshold, character truncation, and 25-file cap; label the list as implementation-defined and cite `pocarchitect/cli.py`.

### DOC-008 — Batch item failures do not produce a documented nonzero command contract

- **Severity:** High
- **Category:** Batch / state
- **Documentation evidence:** Batch documentation explains retries/state but gives no exit-status contract (`docs/command-guide.md:214-248`). Its automation section demonstrates shell gates (`docs/command-guide.md:250-275`), and `test-full.sh` enables `set -e` before its real batch (`test-full.sh:8`, `test-full.sh:51-56`).
- **Implementation/config/test evidence:** Per-item `typer.Exit` and other exceptions are counted, persisted, and followed by “Continuing” (`pocarchitect/cli.py:653-687`); the function emits a summary/failed URLs and returns without a final raise (`pocarchitect/cli.py:689-713`). Tests explicitly cover continued processing after failures (`tests/test_cli.py:53-92`, `tests/test_cli.py:153-190`). The isolated one-item command probe produced `failed=1` with process exit 0.
- **Observed mismatch/omission:** Automation docs do not warn that item failure is represented in output/state rather than necessarily in the process exit, so `set -e` is not sufficient to gate batch success.
- **Affected audience/workflow:** CI, scheduled batches, shell scripts, and any workflow using exit status as success criteria.
- **Concrete documentation correction:** Publish an exit-code contract. For the current behavior, explicitly require consumers to inspect `batch_complete.failed`, JSON state, or `batch-status`; do not imply `set -e` detects per-item failures.

### DOC-009 — Batch dry-run processes only the first eligible URL, but validation text implies batch coverage

- **Severity:** Medium
- **Category:** Batch / state
- **Documentation evidence:** `verify.sh` labels its invocation a “Batch mode dry-run test” and concludes that `--batch` works (`verify.sh:53-58`, `verify.sh:61-68`). General output documentation only says dry runs create no reports (`docs/NOVICE_USABILITY_GUIDE.md:235-237`).
- **Implementation/config/test evidence:** On any dry-run `typer.Exit`, batch processing breaks after the first processed URL (`pocarchitect/cli.py:653-660`) and emits an explicit first-URL message (`pocarchitect/cli.py:702-703`). The test asserts one processed and one skipped for two URLs (`tests/test_cli.py:95-131`).
- **Observed mismatch/omission:** The first-item limit is not in user-facing batch documentation, and the verification script's success statement overstates what it exercises.
- **Affected audience/workflow:** Users previewing an authorized list and maintainers treating `verify.sh` as batch-wide validation.
- **Concrete documentation correction:** State that batch dry-run stops after the first non-resumed URL; rename the script step to “first batch item dry-run,” or loop over input items explicitly if full preview coverage is intended.

### DOC-010 — Batch input grammar is more permissive than “one URL per line” documentation

- **Severity:** Low
- **Category:** Batch / state
- **Documentation evidence:** Command and Docker guides describe or require one URL per line (`docs/command-guide.md:214-221`; `docs/docker-guide.md:68-79`).
- **Implementation/config/test evidence:** The parser discards blank lines and lines whose trimmed content starts with `#` (`pocarchitect/cli.py:588-593`).
- **Observed mismatch/omission:** Comment and blank-line support is an implemented input feature absent from the input-format descriptions.
- **Affected audience/workflow:** Batch-file authors and template maintainers.
- **Concrete documentation correction:** Add a two-line grammar note and example showing that blank lines and full-line `#` comments are ignored; do not claim inline comments are supported because the code does not remove them.

### DOC-011 — The resumable JSON ledger has no documented schema or compatibility contract

- **Severity:** Medium
- **Category:** Batch / state
- **Documentation evidence:** README documents the path and resume rule (`README.md:48-50`); the novice guide documents status/reset and the path (`docs/NOVICE_USABILITY_GUIDE.md:213-227`, `docs/NOVICE_USABILITY_GUIDE.md:235-237`). None of those locations gives a JSON example or field contract.
- **Implementation/config/test evidence:** State currently has top-level `version: 2` and `items` (`pocarchitect/state.py:12-20`); loader validates only a dictionary with dictionary `items` (`pocarchitect/state.py:23-38`); success entries contain `status` and `updated_at`, while failures contain `status` and `error` (`pocarchitect/cli.py:648-680`); summaries count unknown statuses (`pocarchitect/state.py:62-74`).
- **Observed mismatch/omission:** A persistent, operator-inspectable artifact is named but not specified, leaving version, fields, unknown values, and failure text undocumented.
- **Affected audience/workflow:** Recovery tooling, audit retention, state migration, and manual repair.
- **Concrete documentation correction:** Add a version-2 sample and field table, state the minimal accepted shape exactly as implemented, and direct unsupported/corrupt files to the existing recoverable reset path without promising compatibility beyond `load_state`.

### DOC-012 — Report ingestion metadata can assert a clone that did not occur

- **Severity:** High
- **Category:** Outputs / packaging / links
- **Documentation evidence:** The novice guide says successful reports contain metadata/body hash and distinguishes non-GitHub URL-only handling (`docs/NOVICE_USABILITY_GUIDE.md:23-29`); output documentation names the file but not the metadata schema (`docs/NOVICE_USABILITY_GUIDE.md:235-237`). The prior report describes metadata as provenance (`docs/DOCUMENTATION_REVIEW_REPORT.md:39-41`), but was not accepted as ground truth.
- **Implementation/config/test evidence:** `save_report` sets `ingestion` to `github-shallow-clone` whenever `no_ingest` is false (`pocarchitect/cli.py:148-163`). A non-GitHub URL returns limited context without cloning (`pocarchitect/cli.py:292-298`), and a failed GitHub clone returns warning context (`pocarchitect/cli.py:423-425`); both paths can call `save_report(..., no_ingest)` (`pocarchitect/cli.py:552-562`).
- **Observed mismatch/omission:** The artifact's undocumented `ingestion` field records option intent, not demonstrated clone outcome, and can conflict with the directly evidenced execution path.
- **Affected audience/workflow:** Report consumers, auditors, incident records, and anyone using front matter to assess grounding.
- **Concrete documentation correction:** Publish the exact metadata schema and state that the current `ingestion` value is derived only from `--no-ingest`; explicitly warn that it does not prove clone success or GitHub handling until implementation records outcome separately.

### DOC-013 — The source-distribution manifest excludes targets linked by its included README

- **Severity:** Medium
- **Category:** Outputs / packaging / links
- **Documentation evidence:** README links the novice guide and seven documentation pages using repository-relative `docs/...` paths (`README.md:18-20`, `README.md:84-93`).
- **Implementation/config/test evidence:** `MANIFEST.in` explicitly includes `README.md` (`MANIFEST.in:3-6`) and explicitly prunes `docs` and `example_usage` from the source distribution (`MANIFEST.in:18-21`).
- **Observed mismatch/omission:** Under the stated manifest policy, the included README's local documentation targets are excluded from the same source distribution. The repository link validator passes against the checkout but does not validate a built distribution (`scripts/validate_documentation_links.py:10-27`).
- **Affected audience/workflow:** Readers of unpacked source distributions and package metadata rendered outside the Git checkout.
- **Concrete documentation correction:** Either include the referenced docs in the distribution or use absolute repository URLs in the packaged README; add a built-artifact link check only if the project chooses to guarantee those links.

### DOC-014 — The Docker “daily use” alias omits the interactivity required by its default real run

- **Severity:** Medium
- **Category:** Docker
- **Documentation evidence:** The Docker guide says real grounded runs need an interactive terminal and demonstrates `-it` (`docs/docker-guide.md:44-56`); it later defines an alias without `-it` and says to run `pocarch --url <url>` (`docs/docker-guide.md:109-119`).
- **Implementation/config/test evidence:** For unconfirmed ingestion, non-TTY stdin emits `confirmation_required` and exits 2 (`pocarchitect/cli.py:206-237`). The alias also supplies neither `--yes` nor safe `--no-ingest --dry-run` flags (`docs/docker-guide.md:115-119`).
- **Observed mismatch/omission:** The same guide advertises a default alias invocation that cannot follow the confirmation path it says real runs require.
- **Affected audience/workflow:** Docker users adopting the alias for ordinary grounded runs.
- **Concrete documentation correction:** Include `-it` in the interactive alias, or make the alias explicitly safe-preview-only; document a separate noninteractive form with `--yes` only under the guide's existing reviewed/authorized warning.

### DOC-015 — Verification scripts select an inconsistent preflight mode/provider

- **Severity:** High
- **Category:** Scripts / CI
- **Documentation evidence:** `verify.sh` says it validates without real calls, then invokes bare `pocarchitect preflight` (`verify.sh:1-5`, `verify.sh:28-31`). `test-full.sh` says OpenAI is the default and only instructs the operator to set `OPENAI_API_KEY`, then also invokes bare preflight (`test-full.sh:3-16`, `test-full.sh:24-27`). The command guide mentions both scripts but only warns that `test-full.sh` makes real OpenAI calls (`docs/command-guide.md:347-356`).
- **Implementation/config/test evidence:** The `preflight` command defaults to provider `xai`, defaults `offline` false, and requires readiness when not offline (`pocarchitect/cli.py:81-109`). Preflight therefore checks the selected provider's key, with xAI as the default (`pocarchitect/preflight.py:181-190`).
- **Observed mismatch/omission:** The no-call verifier still requires the default xAI credential, while the OpenAI real-call script checks xAI readiness even though its instructions mention only an OpenAI key.
- **Affected audience/workflow:** Contributors running repository verification and operators performing the warned real-call test.
- **Concrete documentation correction:** Change `verify.sh` and its guide entry to `preflight --offline`; change `test-full.sh` to `preflight --provider openai`; document those exact checks beside the script warnings.

### DOC-016 — CI patch/repair scripts conflict with the checked-in workflow and are undocumented

- **Severity:** High
- **Category:** Scripts / CI
- **Documentation evidence:** `apply_ci_fixes.py` describes itself as idempotent and safe to run repeatedly (`scripts/apply_ci_fixes.py:1-5`). The command guide's development/script section lists the generator and two shell scripts but does not identify the CI patcher, its check mode, or the repair script (`docs/command-guide.md:322-356`).
- **Implementation/config/test evidence:** The patcher embeds a one-job `Build and Test` workflow (`scripts/apply_ci_fixes.py:12-54`) and overwrites `.github/workflows/ci.yml` whenever it differs (`scripts/apply_ci_fixes.py:150-176`, `scripts/apply_ci_fixes.py:179-200`). The checked-in workflow instead has five jobs and documentation/security/Docker gates (`.github/workflows/ci.yml:16-160`). The fallback template embeds a third workflow variant and can add a Black target block (`scripts/apply_ci_fixes.template.py:12-60`, `scripts/apply_ci_fixes.template.py:167-214`); repair can write that template (`scripts/repair_apply_ci_fixes.py:80-87`). The only direct patcher test checks for diff-text contamination, not equivalence to current CI (`tests/test_ci_fixes_script.py:4-12`). Read-only `--check` reported one required change.
- **Observed mismatch/omission:** A script advertised as safe would replace the current multi-job workflow with a materially different literal; the repair fallback can restore a different patcher again. No operator documentation warns about this write scope or drift.
- **Affected audience/workflow:** Maintainers repairing CI, contributors following script names, and branch protection relying on current jobs.
- **Concrete documentation correction:** Until the literals are reconciled, mark both patch/repair scripts as maintenance-only and not safe for current CI; document `--check`, every path they may rewrite, backup/review steps, and the exact intended workflow source of truth.

### DOC-017 — Configuration reference provenance is described as implementation-generated but is a static literal

- **Severity:** Medium
- **Category:** Documentation tooling / validation
- **Documentation evidence:** README says both canonical CLI and configuration references are generated “from the command metadata” (`README.md:78-82`), and the configuration page says it is generated “from the current implementation” (`docs/configuration-reference.md:1-4`).
- **Implementation/config/test evidence:** The CLI page is built from Typer/Click metadata (`scripts/generate_docs.py:28-89`), but the complete configuration page is a hand-maintained `CONFIG_REFERENCE` string (`scripts/generate_docs.py:92-135`) that is merely written/compared (`scripts/generate_docs.py:138-158`).
- **Observed mismatch/omission:** The configuration file is generated as a file but its settings are not derived from implementation metadata; the provenance claim overstates the drift protection.
- **Affected audience/workflow:** Maintainers changing keys/defaults, reviewers trusting `--check`, and users treating source locations as automatically synchronized.
- **Concrete documentation correction:** Say that configuration content is maintained in `scripts/generate_docs.py`, or derive its rows from exported constants/option metadata. Keep the narrower “metadata-generated” claim only for the CLI reference unless the generator changes.

### DOC-018 — Contributor commands do not reproduce the current CI gates

- **Severity:** Medium
- **Category:** Scripts / CI
- **Documentation evidence:** The development section lists `pytest`, `ruff check`, Black, `mypy pocarchitect`, and `pip-audit`, then separately lists document generation and the two shell scripts (`docs/command-guide.md:322-356`).
- **Implementation/config/test evidence:** CI also runs `ruff format --check`, types both `pocarchitect` and `tests`, checks generated docs, validates novice guides and links (`.github/workflows/ci.yml:39-58`), runs coverage and Codecov (`.github/workflows/ci.yml:88-96`), performs Docker build/help (`.github/workflows/ci.yml:125-136`), and builds distributions (`.github/workflows/ci.yml:138-160`).
- **Observed mismatch/omission:** The documented local gate differs in mypy scope and omits several required quality checks; no CI job map explains what is and is not locally reproducible.
- **Affected audience/workflow:** Pull-request authors and maintainers diagnosing CI-only failures.
- **Concrete documentation correction:** Add a “match CI locally” block with the exact quality commands and a separate table for test/security/Docker/build jobs, explicitly labeling coverage upload and hosted-run outcomes as CI-only.

### DOC-019 — Documentation validators prove structure/local targets, not command accuracy

- **Severity:** Medium
- **Category:** Documentation tooling / validation
- **Documentation evidence:** The prior report describes a link validation and says novice guides and the command ledger were validated (`docs/DOCUMENTATION_REVIEW_REPORT.md:115-126`, `docs/DOCUMENTATION_REVIEW_REPORT.md:179-188`).
- **Implementation/config/test evidence:** The novice validator checks heading counts and required substrings (`scripts/validate_novice_guides.py:35-76`); its test only executes that script (`tests/test_novice_guides.py:8-16`). The link validator includes only `.md` files under selected sources, so the listed `POCArchitect_Quickstart.txt` source is rejected by its own suffix condition and the packaged prompt is outside `DOC_SOURCES` (`scripts/validate_documentation_links.py:10-27`); it skips HTTP(S) (`scripts/validate_documentation_links.py:43-62`). Its test only executes the script (`tests/test_documentation_links.py:8-16`).
- **Observed mismatch/omission:** Passing controls do not establish shell syntax, option validity, external link reachability, prompt links, or the root `.txt` quickstart—the exact areas where current gaps remain.
- **Affected audience/workflow:** Maintainers interpreting green CI as documentation correctness.
- **Concrete documentation correction:** Rename/control descriptions to “required-string/heading” and “selected local Markdown link” validation; publish scope exclusions; add metadata-based command parsing or safe command probes only for commands the project intends CI to validate.

### DOC-020 — Platform support wording includes an unsubstantiated 64-bit restriction and omits macOS from the matrix

- **Severity:** Medium
- **Category:** Platform instructions
- **Documentation evidence:** Both supplements require a “64-bit” operating system (`docs/guides/WINDOWS_NOVICE_USABILITY_GUIDE.md:54-56`; `docs/guides/LINUX_NOVICE_USABILITY_GUIDE.md:54-56`). The command guide provides a combined macOS/Linux install path (`docs/command-guide.md:42-51`), and the canonical guide says macOS was not independently tested (`docs/NOVICE_USABILITY_GUIDE.md:35-40`), but the README support matrix has no macOS row (`README.md:39-46`).
- **Implementation/config/test evidence:** Packaging declares only Python `>=3.10` (`pyproject.toml:1-7`); preflight checks only the Python version for platform suitability (`pocarchitect/preflight.py:155-160`); CI runs Ubuntu without a repository-declared architecture condition (`.github/workflows/ci.yml:60-89`).
- **Observed mismatch/omission:** The tracked implementation/configuration does not establish the supplements' 64-bit requirement, while a documented macOS path lacks a matching status row.
- **Affected audience/workflow:** 32-bit-environment users, macOS users, and support triage.
- **Concrete documentation correction:** Recast 64-bit as a recommendation unless a checked requirement is added; add a macOS row labeled with the canonical guide's explicit “not independently tested” status.

### DOC-021 — Platform guides contradict themselves about local-provider keys and give an xAI-specific generic check

- **Severity:** Medium
- **Category:** Preflight / configuration
- **Documentation evidence:** Both platform guides say “Normal runs require a provider key” (`docs/guides/WINDOWS_NOVICE_USABILITY_GUIDE.md:31-33`; `docs/guides/LINUX_NOVICE_USABILITY_GUIDE.md:31-33`), then say local providers need no cloud key (`docs/guides/WINDOWS_NOVICE_USABILITY_GUIDE.md:86-96`; `docs/guides/LINUX_NOVICE_USABILITY_GUIDE.md:86-96`). Their API-key troubleshooting verifies with bare `preflight` (`docs/guides/WINDOWS_NOVICE_USABILITY_GUIDE.md:39-46`; `docs/guides/LINUX_NOVICE_USABILITY_GUIDE.md:39-46`).
- **Implementation/config/test evidence:** Preflight's default provider is xAI (`pocarchitect/cli.py:88-90`); local uses endpoint readiness instead of a cloud key (`pocarchitect/preflight.py:181-190`). The configuration table lists `local` among providers and keys only for the three cloud providers (`docs/configuration-reference.md:12-17`, `docs/configuration-reference.md:27-30`).
- **Observed mismatch/omission:** The same documents both require and exempt a key for local runs, while the generic diagnostic command can check xAI rather than the provider that failed.
- **Affected audience/workflow:** Local, OpenAI, and Groq users following platform troubleshooting.
- **Concrete documentation correction:** Change “Normal runs” to “Real cloud-provider runs”; make every diagnostic command include the same `--provider` (and local `--base-url`) as the failed run.

### DOC-022 — Placeholder batch values are fed to the documented real-call test

- **Severity:** Medium
- **Category:** Examples
- **Documentation evidence:** `example_usage/batch_urls.txt` contains `CVE-2024-XXXXX` and another generic repository value with no in-file placeholder warning (`example_usage/batch_urls.txt:1-2`). The quickstart tells users to run that file with xAI (`POCArchitect_Quickstart.txt:97-102`). `test-full.sh` warns that it consumes OpenAI credits and then uses the same file for its real batch (`test-full.sh:10-16`, `test-full.sh:51-56`).
- **Implementation/config/test evidence:** Batch accepts every nonblank/noncomment line without URL validation (`pocarchitect/cli.py:588-603`) and sends each eligible item through `process_single_url` (`pocarchitect/cli.py:619-646`).
- **Observed mismatch/omission:** A file containing visibly illustrative values is presented as input to billable real-provider workflows without an instruction to replace or validate every URL.
- **Affected audience/workflow:** Users copying the quickstart and maintainers running the full test.
- **Concrete documentation correction:** Put a leading comment in the batch file declaring all values placeholders, require replacement with authorized reachable URLs before a real run, and use a separate safe fixture for dry-run verification.

### DOC-023 — Complete model defaults and Claude/Gemini compatibility boundaries are not documented together

- **Severity:** Low
- **Category:** Providers / models
- **Documentation evidence:** README and architecture give only xAI/OpenAI examples for provider-specific defaults (`README.md:58-60`; `docs/architecture.md:50-56`). The packaged prompt names Claude and Gemini compatibility (`pocarchitect/POC_Architect_Prompt.md:1-5`), while the public reference lists only xAI, OpenAI, Groq, and local (`docs/cli-reference.md:11-16`).
- **Implementation/config/test evidence:** The exact four defaults are declared at `pocarchitect/cli.py:72-78`, and the CLI provider choice is limited to those four values (`pocarchitect/cli.py:797-799`).
- **Observed mismatch/omission:** No single provider table exposes the Groq default or clarifies that Claude/Gemini wording describes prompt portability rather than a named CLI provider surface.
- **Affected audience/workflow:** Users selecting models and readers interpreting the packaged prompt header.
- **Concrete documentation correction:** Add the exact four-value default-model table and state only that the current CLI offers the four declared provider choices; describe any other endpoint compatibility only to the extent configured through `local`/`--base-url`.

### DOC-024 — “Preflight readiness” lacks an exact limitations statement

- **Severity:** Medium
- **Category:** Preflight / configuration
- **Documentation evidence:** README says offline preflight verifies Python, installed packages, entry point, prompt, and output directory (`README.md:30-37`); the novice guide repeats that list (`docs/NOVICE_USABILITY_GUIDE.md:180-186`). Git is separately presented as a prerequisite (`docs/NOVICE_USABILITY_GUIDE.md:35-39`). The Ollama guide says its helper tests chat completions, then directs users to POCArchitect preflight for the endpoint (`docs/ollama-setup-guide.md:40-55`).
- **Implementation/config/test evidence:** Package preflight's exact import list is five names and has no Git executable check (`pocarchitect/preflight.py:30`, `pocarchitect/preflight.py:162-179`). Git is later invoked by grounding (`pocarchitect/cli.py:310-328`). Local preflight performs only an HTTP request to `<base>/models` (`pocarchitect/preflight.py:72-84`); the separate Ollama helper checks `/api/version`, `/api/show`, and `/v1/chat/completions` (`docs/ollama_preflight_check.py:30-83`).
- **Observed mismatch/omission:** The high-level wording does not say that Git and chat-completion/model suitability are outside POCArchitect preflight's checks.
- **Affected audience/workflow:** Installation verification and local-provider readiness diagnosis.
- **Concrete documentation correction:** Publish the exact check list and explicit non-checks: no Git executable test and, for local, only `/models` HTTP readiness; keep the helper's three additional checks separately named.

### DOC-025 — The `slow` marker says “skipped by default,” but no default exclusion is configured

- **Severity:** Low
- **Category:** Tests / test configuration
- **Documentation evidence:** Pytest metadata describes `slow` as “skipped BY default” (`pytest.ini:12-18`).
- **Implementation/config/test evidence:** Default `addopts` contains quiet/traceback/strict/maxfail options but no marker exclusion (`pytest.ini:5-10`), and CI invokes unfiltered `pytest --cov=...` (`.github/workflows/ci.yml:88-90`).
- **Observed mismatch/omission:** The declared default skip policy is not represented in the repository's pytest or CI command configuration.
- **Affected audience/workflow:** Test authors and contributors deciding whether slow tests run.
- **Concrete documentation correction:** Remove “skipped by default” unless an explicit skip/filter is configured; if configured later, document the exact marker expression.

### DOC-026 — Platform supplements duplicate the canonical journey and themselves

- **Severity:** Low
- **Category:** Duplication / maintainability
- **Documentation evidence:** Each supplement gives a complete install/safe-run/provider/batch/troubleshooting summary at the top (`docs/guides/WINDOWS_NOVICE_USABILITY_GUIDE.md:7-48`; `docs/guides/LINUX_NOVICE_USABILITY_GUIDE.md:7-48`) and then repeats those topics as many small sections (`docs/guides/WINDOWS_NOVICE_USABILITY_GUIDE.md:50-156`; `docs/guides/LINUX_NOVICE_USABILITY_GUIDE.md:50-156`). Both also point readers to the canonical guide (`docs/guides/WINDOWS_NOVICE_USABILITY_GUIDE.md:3-5`; `docs/guides/LINUX_NOVICE_USABILITY_GUIDE.md:3-5`).
- **Implementation/config/test evidence:** The validator requires at least 30 second-level headings in each supplement (`scripts/validate_novice_guides.py:35-44`) plus string presence (`scripts/validate_novice_guides.py:45-58`), rather than checking that the supplements contain only platform deltas.
- **Observed mismatch/omission:** Three novice journeys duplicate the same behavior, increasing the already demonstrated risk of contradictory provider/preflight wording (DOC-021); the automated heading threshold reinforces the duplication.
- **Affected audience/workflow:** Novices choosing a source of truth and maintainers updating commands.
- **Concrete documentation correction:** Keep the canonical guide authoritative; reduce supplements to shell/path/platform deltas plus their ledgers, and replace the heading-count rule with checks for required platform-specific content and canonical links.

### DOC-027 — The prior review report is linked as documentation without a prominent historical-snapshot boundary

- **Severity:** Low
- **Category:** Historical documentation
- **Documentation evidence:** The report states that it reviewed commit `60d55...`, a different local path, and a specific environment (`docs/DOCUMENTATION_REVIEW_REPORT.md:18-27`), then records point-in-time command outcomes (`docs/DOCUMENTATION_REVIEW_REPORT.md:115-129`). README lists it alongside current references as a “traceability matrix and validation record for this review” (`README.md:84-93`).
- **Implementation/config/test evidence:** The report's link-validation result says 14 files (`docs/DOCUMENTATION_REVIEW_REPORT.md:122-125`), while the current validator's selected scope is dynamically enumerated (`scripts/validate_documentation_links.py:20-27`) and the current command result was 15. Current `git rev-parse HEAD` produced `0c457...`, not the report's baseline.
- **Observed mismatch/omission:** The document contains an internal commit marker, but its navigation entry lacks a clear “historical snapshot; do not use as current behavior/validation evidence” label.
- **Affected audience/workflow:** Auditors and maintainers looking for current status.
- **Concrete documentation correction:** Add a banner at the report top and README link text naming its reviewed commit/date and historical status; keep current validation results in generated CI artifacts rather than updating a snapshot silently.

### DOC-028 — Ollama helper success language exceeds its documented checks

- **Severity:** Low
- **Category:** Local-provider helper
- **Documentation evidence:** The Ollama guide limits claims, says service/model behavior is external, and states no live endpoint was run in that review (`docs/ollama-setup-guide.md:5-10`, `docs/ollama-setup-guide.md:72-81`).
- **Implementation/config/test evidence:** The helper performs three bounded checks (`docs/ollama_preflight_check.py:30-83`) but prints “OLLAMA IS PERFECTLY READY” and “ready for red-team use” on success (`docs/ollama_preflight_check.py:86-121`). No tracked test targets this helper; the eight test modules listed in Appendix A target other files.
- **Observed mismatch/omission:** The absolute success message conflicts with the guide's narrower readiness/response limitations and the helper's finite checks.
- **Affected audience/workflow:** Local-provider operators interpreting a helper pass as end-to-end readiness.
- **Concrete documentation correction:** Change the panel to “the three listed checks passed,” name the model/base URL tested, and state that POCArchitect's full prompt, report generation, response quality, and resource sufficiency were not tested by the helper.

## 6. Internal contradiction and duplication analysis

### 6.1 Direct contradictions

| Topic | Side A | Side B | Resolution represented by finding |
|---|---|---|---|
| Mitigation flag and label validation | Quickstart advertises `--no-include-mitigations` and enumerated labels (`POCArchitect_Quickstart.txt:103-112`). | Canonical reference says strings are free text and there is no disable switch (`docs/cli-reference.md:18-21`); declarations match the canonical side (`pocarchitect/cli.py:812-826`). | DOC-002 |
| Batch machine output | CLI reference calls `batch-status` machine-readable (`docs/cli-reference.md:42-45`). | Configuration, novice, and command references say batch subcommands are not JSON Lines (`docs/configuration-reference.md:41-43`; `docs/command-guide.md:250-259`). | DOC-003; implementation's global `--format` path is at `pocarchitect/cli.py:847-859`. |
| Local-provider credential | Platform guides say normal runs require a key (`docs/guides/WINDOWS_NOVICE_USABILITY_GUIDE.md:31-33`; `docs/guides/LINUX_NOVICE_USABILITY_GUIDE.md:31-33`). | The same guides say local needs no cloud key (`docs/guides/WINDOWS_NOVICE_USABILITY_GUIDE.md:90-92`; `docs/guides/LINUX_NOVICE_USABILITY_GUIDE.md:90-92`). | DOC-021 |
| Docker confirmation | Real runs are documented with `-it` (`docs/docker-guide.md:44-56`). | The recommended alias omits it, `--yes`, and dry-run flags (`docs/docker-guide.md:109-119`). | DOC-014 |
| Generated-reference provenance | README says CLI and configuration are generated from command metadata (`README.md:78-82`). | Generator derives CLI rows from metadata but stores configuration as a literal (`scripts/generate_docs.py:62-135`). | DOC-017 |
| Report-saving path | Architecture names the package CLI for orchestration but bare `cli.py` for report saving (`docs/architecture.md:37-44`). | Packaging selects `pocarchitect.cli:app` (`pyproject.toml:23-24`), while a separate root `cli.py` also has a writer (`cli.py:75-84`). | DOC-001 |
| Slow-test default | Marker text says slow tests are skipped by default (`pytest.ini:12-18`). | Default options and CI contain no slow-marker filter (`pytest.ini:5-10`; `.github/workflows/ci.yml:88-90`). | DOC-025 |

### 6.2 Duplication and drift exposure

- Four manually maintained option summaries overlap the generated reference: `README.md:52-70`, `POCArchitect_Quickstart.txt:103-114`, `docs/agentusage.md:5-25`, and `docs/command-guide.md:149-170`; the generated source is `scripts/generate_docs.py:28-89`. DOC-002 demonstrates current drift in one copy.
- The canonical guide covers the complete journey (`docs/NOVICE_USABILITY_GUIDE.md:15-310`), while each platform supplement first summarizes and then repeats the same journey (`docs/guides/WINDOWS_NOVICE_USABILITY_GUIDE.md:7-156`; `docs/guides/LINUX_NOVICE_USABILITY_GUIDE.md:7-156`). The validator's 30-heading rule is explicit at `scripts/validate_novice_guides.py:35-44` (DOC-026).
- Two root runtime-looking files overlap package files but materially differ (`cli.py:23-50`, `cli.py:464-564`, `preflight.py:14-161` versus `pocarchitect/cli.py:27-109`, `pocarchitect/cli.py:716-931`, `pocarchitect/preflight.py:21-233`), with no status note (DOC-001).
- `scripts/apply_ci_fixes.py` and its template contain different workflow literals and different patch scopes (`scripts/apply_ci_fixes.py:12-176`; `scripts/apply_ci_fixes.template.py:12-214`), while repair can substitute the template (`scripts/repair_apply_ci_fixes.py:80-87`) (DOC-016).

## 7. Generated, stale, and historical document analysis

| Artifact | Evidence-supported classification | Analysis |
|---|---|---|
| `docs/cli-reference.md` | **Generated artifact** | It identifies its generator (`docs/cli-reference.md:1-4`), and the generator derives tables from Click/Typer metadata (`scripts/generate_docs.py:28-89`). Freshness was **not determinable in this environment** because `--check` could not import a declared runtime dependency; no stale claim is made. |
| `docs/configuration-reference.md` | **Generated file from a static source literal** | It identifies itself as generated (`docs/configuration-reference.md:1-4`), but content lives literally at `scripts/generate_docs.py:92-135` (DOC-017). Current textual equality was not established by the blocked generator command. |
| `docs/DOCUMENTATION_REVIEW_REPORT.md` | **Historical snapshot** | It binds itself to commit `60d55...`, a path, and an environment (`docs/DOCUMENTATION_REVIEW_REPORT.md:18-27`) and records point-in-time command results (`docs/DOCUMENTATION_REVIEW_REPORT.md:115-129`). Current HEAD differed in the read-only Git result (DOC-027). |
| `POCArchitect_Quickstart.txt` | **Demonstrably out of sync; maintainer-intended historical status not determinable** | Its options conflict with current declarations (`POCArchitect_Quickstart.txt:103-112`; `pocarchitect/cli.py:812-826`) and its commands differ from canonical syntax (DOC-002). The prior report calls it “Legacy” and recommends retirement (`docs/DOCUMENTATION_REVIEW_REPORT.md:47-52`, `docs/DOCUMENTATION_REVIEW_REPORT.md:103-113`), but that prior label was not used as proof of maintainer intent. |
| `docs/POCArchitect_Example_Report.md` | **Explicit static example, not treated as stale runtime documentation** | Its warning says it is non-functional and illustrative (`docs/POCArchitect_Example_Report.md:1-4`). No runtime-validity inference was drawn from its sample commands or code. |
| `scripts/apply_ci_fixes.py` embedded workflow | **Current-tree drift proven** | Its overwrite literal (`scripts/apply_ci_fixes.py:12-54`) differs visibly from the checked-in five-job workflow (`.github/workflows/ci.yml:16-160`), and its read-only `--check` returned one change (DOC-016). |

No other file is labeled stale or generated merely because of age, duplication, or a date string. The prompt's own version/date (`pocarchitect/POC_Architect_Prompt.md:1-5`) and the example report's date (`docs/POCArchitect_Example_Report.md:5-10`) are recorded content, not proof of staleness.

## 8. Link, reference, and path correctness

1. **Baseline checkout local Markdown targets:** the existing validator passed 15 selected Markdown files. Its selection and resolution logic is at `scripts/validate_documentation_links.py:10-62`; this establishes only existence/anchor checks for that scope.
2. **External URLs:** the validator deliberately skips `http://`, `https://`, and `mailto:` (`scripts/validate_documentation_links.py:46-49`), so current reachability of provider, installer, issue, and repository URLs is **Not Determinable** from repository contents.
3. **Excluded documentation sources:** despite listing `POCArchitect_Quickstart.txt`, the validator accepts a source file only when its suffix is `.md`, and its directory scan also selects only `*.md` (`scripts/validate_documentation_links.py:10-27`). The packaged prompt is not in `DOC_SOURCES` (`scripts/validate_documentation_links.py:10-16`) (DOC-019).
4. **Distribution-relative targets:** README's `docs/...` links (`README.md:18-20`, `README.md:84-93`) conflict with the sdist prune policy (`MANIFEST.in:18-21`) (DOC-013).
5. **Ambiguous source path:** architecture's bare `cli.py` report-saving path (`docs/architecture.md:37-44`) is ambiguous because both `cli.py` and `pocarchitect/cli.py` are tracked and contain different save routines (`cli.py:75-84`; `pocarchitect/cli.py:134-165`) (DOC-001).
6. **Untracked review output:** `.gitignore` explicitly excludes `/review-output/` (`.gitignore:24-25`), and Git returned no tracked path there; it was neither link-validated nor used as evidence.

No broken local Markdown target was established in the baseline checkout. DOC-013 is a packaging-context path gap, not a claim that the checkout links are broken.

## 9. Prioritized remediation

Ordering is severity first, then breadth of affected workflow. Each row is derived only from the cited finding(s).

| Priority | Remediation | Finding IDs | Evidence-bound acceptance criterion |
|---|---|---|---|
| P0 | Declare one authoritative CLI/preflight tree and explain/remove ambiguity. | DOC-001 | Architecture names `pocarchitect/cli.py` consistently and states the status of root `cli.py`/`preflight.py` without unsupported intent claims. |
| P0 | Retire or fully synchronize the root quickstart. | DOC-002 | No absent negative mitigation flag, no fixed-value claim for string options, and every multi-line command has valid continuation/fencing. |
| P0 | Correct batch automation output and exit guidance. | DOC-003, DOC-008 | Docs show global JSON option placement and explicitly state how a caller detects `failed > 0`; examples do not rely on `set -e` alone. |
| P0 | Document the actual automatic-preflight path semantics. | DOC-004, DOC-005 | Docs say dry run skips all automatic checks and say `--output-dir`/`IN_DOCKER` do not currently alter preflight's tested path. |
| P0 | Disclose clone-failure fallback before provider approval. | DOC-006 | Architecture/troubleshooting state that warning context can proceed and tell users what preview text to inspect. |
| P0 | Correct report provenance documentation. | DOC-012 | Front-matter keys are listed and `ingestion` is explicitly defined as the current flag-derived value, not proof of clone success. |
| P0 | Fix verification preflight commands. | DOC-015 | `verify.sh` documents/uses offline preflight; `test-full.sh` documents/uses OpenAI preflight. |
| P0 | Reconcile or quarantine CI patch/repair scripts. | DOC-016 | One reviewed workflow source is named; script write scope and `--check` are documented; embedded literals no longer silently conflict. |
| P1 | Complete grounding, state, and preflight specifications. | DOC-007, DOC-011, DOC-024 | Tables cover selection thresholds, ledger v2 fields, exact checks, Git non-check, and local `/models` scope. |
| P1 | Document batch first-item dry run and comment grammar. | DOC-009, DOC-010 | Batch guide states first eligible item only and shows blank/full-line-comment handling. |
| P1 | Repair packaging and Docker guidance. | DOC-013, DOC-014 | Packaged README targets resolve in the intended artifact context; Docker alias is explicitly interactive or preview-only. |
| P1 | Make contributor/validation documentation match actual control scope. | DOC-017, DOC-018, DOC-019 | Generator provenance is truthful, exact CI commands are listed, and validators are labeled by their real coverage. |
| P1 | Reconcile platform/provider/example wording. | DOC-020, DOC-021, DOC-022 | Platform matrix includes macOS status, unsupported 64-bit requirement is removed/qualified, local key wording is consistent, and real-call examples require replacement of placeholders. |
| P2 | Publish the exact provider default map and compatibility boundary. | DOC-023 | One table names all four defaults and distinguishes CLI choices from prompt portability. |
| P2 | Correct test-marker metadata and reduce guide duplication. | DOC-025, DOC-026 | Slow-marker wording matches configured invocation; supplements contain platform deltas rather than repeated full journeys. |
| P2 | Label historical review evidence and narrow helper success language. | DOC-027, DOC-028 | Review link/banner names its snapshot commit; helper reports only its three completed checks. |

## 10. Remediation closure matrix

The final matrix is populated from the completed, validated tree. Every evidence
cell uses recalculated current `path:line` citations. Its fingerprint binds each
finding to its citation coordinates and normalized cited-file content so line-
ending conversion does not create drift while evidence or coordinate changes do.

<!-- closure-evidence-sha256: 418ab987d683b128a76774bcc9aa1734426c315f9807ba61417c6c5ebe1be181 -->

| Finding | Status | Current evidence | Verified resolution |
|---|---|---|---|
| DOC-001 | Closed | `docs/architecture.md:15-22`; `tests/test_entrypoints.py:4-10` | The divergent root implementations were deleted; both supported invocations resolve to the package app, and an absence test prevents reintroduction. |
| DOC-002 | Closed | `POCArchitect_Quickstart.txt:1-18`; `docs/cli-reference.md:14-23`; `scripts/validate_documentation_reports.py:161-164` | The root quickstart is a canonical redirect rather than a duplicate option list; generated metadata exposes the real paired mitigation option, and the report control rejects the obsolete flag spelling. |
| DOC-003 | Closed | `docs/cli-reference.md:88-98`; `tests/test_cli.py:305-358` | Generated guidance places root format options before subcommands, and status/reset tests verify JSON events. |
| DOC-004 | Closed | `pocarchitect/cli.py:1408-1420`; `pocarchitect/preflight.py:115-128`; `tests/test_cli.py:379-397` | Main resolves the report path before preflight, passes it through, and the standalone preflight accepts the same explicit output option. |
| DOC-005 | Closed | `docs/architecture.md:37-41`; `tests/test_cli.py:400-419` | Current guidance says dry run bypasses all automatic preflight, and the CLI test proves the preflight callback is not invoked. |
| DOC-006 | Closed | `docs/architecture.md:93-106`; `pocarchitect/cli.py:649-657`; `tests/test_cli.py:251-263` | Ingestion failures retain a visible warning, return an explicit URL-only outcome, and are documented as requiring operator rejection unless reduced context is acceptable. |
| DOC-007 | Closed | `docs/architecture.md:108-122`; `pocarchitect/cli.py:558-646` | The architecture lists every keyword, extension, byte threshold, character limit, file cap, and ordering/completeness boundary. |
| DOC-008 | Closed | `pocarchitect/cli.py:1017-1041`; `docs/command-guide.md:246-256`; `tests/test_cli.py:53-94` | Batch processing still attempts later items but raises exit 1 after the summary when failures exist; docs and tests define the contract. |
| DOC-009 | Closed | `pocarchitect/cli.py:972-985`; `tests/test_cli.py:97-133`; `verify.sh:53-59` | Dry run continues through every eligible item, the two-item behavior is tested, and the verifier uses a safe multi-item fixture. |
| DOC-010 | Closed | `pocarchitect/cli.py:876-881`; `docs/command-guide.md:211-221` | Batch grammar explicitly covers blank lines, full-line comments, and the lack of inline-comment stripping. |
| DOC-011 | Closed | `pocarchitect/state.py:23-43`; `docs/command-guide.md:258-294`; `tests/test_state.py:7-16` | Version 2 and object-valued items are enforced without overwrite; the schema, unknown status boundary, timestamps, errors, and recoverable reset are documented. |
| DOC-012 | Closed | `pocarchitect/cli.py:276-356`; `docs/architecture.md:124-131`; `tests/test_cli.py:221-263` | Report metadata records the actual grounding outcome and selected-file count, with tests for disabled, non-GitHub, and failed-ingestion paths. |
| DOC-013 | Closed | `MANIFEST.in:18-29`; `scripts/validate_distribution.py:20-85`; `tests/test_distribution.py:25-61` | Documentation, examples, and the workflow linked by release-readiness guidance are included in the sdist; built-archive local Markdown targets plus both reports are validated. |
| DOC-014 | Closed | `docs/docker-guide.md:113-132`; `tests/test_documentation_contracts.py:6-10` | The real-run alias includes interactive terminal flags and a separate no-provider preview alias is documented and tested. |
| DOC-015 | Closed | `verify.sh:28-51`; `test-full.sh:51-53`; `tests/test_repository_scripts.py:11-24` | The no-network script uses offline preflight and disables ingestion for every URL or batch dry run, while the billable OpenAI script checks the OpenAI provider; per-command contract tests cover both. |
| DOC-016 | Closed | `scripts/validate_ci_workflow.py:8-68`; `tests/test_ci_workflow.py:16-34`; `docs/command-guide.md:397-400` | All mutating patch/template/repair scripts were retired; a read-only validator enforces the sole canonical workflow, release-readiness job, and their continued absence. |
| DOC-017 | Closed | `pocarchitect/config.py:8-32`; `scripts/generate_docs.py:95-121`; `tests/test_generate_docs.py:30-38` | Provider maps and effective defaults come from shared runtime constants; generated text truthfully identifies which prose remains maintained in the generator. |
| DOC-018 | Closed | `docs/command-guide.md:346-381`; `.github/workflows/ci.yml:147-235`; `scripts/validate_fresh_install.py:1-112`; `scripts/release_readiness.py:70-117`; `scripts/release_readiness.py:280-301`; `scripts/release_readiness.py:318-356`; `scripts/release_readiness.py:655-687`; `tests/test_release_readiness.py:21-27` | The local reproduction section mirrors every gate; CI uploads one exact artifact set, clean-installs wheels across Linux/Windows/macOS and supported Python boundaries plus the sdist, checks dependencies, and requires the generated console executable; release readiness also inventories options, probes output, and verifies confirmation against a hermetic provider. |
| DOC-019 | Closed | `scripts/validate_documentation_links.py:10-20`; `scripts/validate_documentation_commands.py:19-126`; `scripts/validate_documentation_reports.py:21-139`; `docs/command-guide.md:383-395` | Link scope includes every documentation tree and prompt; selected safe commands execute; report fingerprints normalize line endings and bind finding/citation coordinates; all controls state their non-goals. |
| DOC-020 | Closed | `README.md:56-64`; `docs/NOVICE_USABILITY_GUIDE.md:3-12`; `docs/guides/WINDOWS_NOVICE_USABILITY_GUIDE.md:1-15`; `docs/guides/LINUX_NOVICE_USABILITY_GUIDE.md:1-16` | Current platform pages consistently describe the clean-install CI gates without claiming hosted success for the current commit; unsupported processor-architecture requirements remain removed. |
| DOC-021 | Closed | `docs/guides/WINDOWS_NOVICE_USABILITY_GUIDE.md:52-64`; `docs/guides/LINUX_NOVICE_USABILITY_GUIDE.md:45-57` | Platform deltas distinguish cloud keys from local operation and show provider-matched OpenAI/local diagnostics including local base URL. |
| DOC-022 | Closed | `example_usage/batch_urls.txt:1-4`; `test-full.sh:22-35`; `tests/test_repository_scripts.py:30-50`; `tests/test_repository_scripts.py:53-63` | The real template is prominently marked; the billable script canonicalizes and rejects equivalent relative or absolute protected paths; executable tests cover both fixtures and dry-run verification remains separate. |
| DOC-023 | Closed | `pocarchitect/config.py:14-25`; `README.md:77-89`; `pocarchitect/POC_Architect_Prompt.md:1-3` | All four model defaults are published from shared constants and Claude/Gemini wording is explicitly bounded to prompt portability. |
| DOC-024 | Closed | `pocarchitect/preflight.py:72-128`; `pocarchitect/preflight.py:175-264`; `docs/architecture.md:73-89` | Preflight checks Git in addition to the exact import/runtime surfaces, gives actionable remediation, uses the resolved output path, and limits local readiness to the models endpoint. |
| DOC-025 | Closed | `pytest.ini:12-19`; `tests/test_documentation_contracts.py:13-18` | The slow marker states that tests are included unless an invocation filters them, with a regression assertion against the old claim. |
| DOC-026 | Closed | `docs/guides/WINDOWS_NOVICE_USABILITY_GUIDE.md:1-10`; `docs/guides/LINUX_NOVICE_USABILITY_GUIDE.md:1-10`; `scripts/validate_novice_guides.py:57-78`; `tests/test_novice_guides.py:29-34` | Platform pages are concise deltas linked to the canonical guide; validation checks platform content and ledgers instead of enforcing duplicated heading counts. |
| DOC-027 | Closed | `docs/DOCUMENTATION_REVIEW_REPORT.md:1-9`; `README.md:137-139`; `scripts/validate_documentation_reports.py:141-159` | The prior report has a top historical-snapshot banner, both reports are accurately characterized in navigation, and CI enforces those boundaries. |
| DOC-028 | Closed | `docs/ollama_preflight_check.py:86-125`; `docs/ollama-setup-guide.md:47-59`; `tests/test_ollama_preflight_check.py:23-39` | Helper success names the tested URL/model and only the three completed checks; guide and test preserve the full-prompt, report, quality, and resource limitations. |

## Appendix A. Complete baseline tracked-file coverage ledger

**Set verification:** PASS — a fresh baseline `git ls-files -z` set equaled the ledger set exactly: 54 files on each side, 0 missing, 0 extra. Every row below records `Fully read: Yes`. Line counts use the baseline working-tree bytes and Python `splitlines()`.

| Tracked path | Lines | Read status | Role | Used by report |
|---|---:|---|---|---|
| `.dockerignore` | 66 | Fully read: Yes | Docker build-context exclusion policy | Section 4 Docker; Appendix A |
| `.env.example` | 14 | Fully read: Yes | Provider credential template | Section 3 inventory; Section 4 configuration |
| `.github/workflows/ci.yml` | 160 | Fully read: Yes | GitHub Actions CI configuration | Section 4 CI/tests/platform; DOC-016, DOC-018, DOC-020, DOC-025 |
| `.gitignore` | 74 | Fully read: Yes | Git/untracked artifact exclusion policy | Section 1 scope; Section 8 links/paths |
| `Dockerfile` | 33 | Fully read: Yes | Container build/runtime definition | Section 4 Docker; DOC-014 |
| `LICENSE` | 23 | Fully read: Yes | License policy | Section 3 inventory |
| `MANIFEST.in` | 25 | Fully read: Yes | Source-distribution inclusion policy | Section 4 packaging; DOC-013; Section 8 |
| `POCArchitect_Quickstart.txt` | 128 | Fully read: Yes | Root beginner quickstart | Section 3 inventory; DOC-002, DOC-022; Section 6 |
| `README.md` | 105 | Fully read: Yes | Repository landing documentation | Section 3 inventory; Section 4; DOC-005, DOC-013, DOC-017, DOC-020, DOC-023, DOC-024, DOC-027 |
| `cli.py` | 564 | Fully read: Yes | Separate root CLI implementation | Section 4 entry points; DOC-001; Section 6/8 |
| `docs/DOCUMENTATION_REVIEW_REPORT.md` | 193 | Fully read: Yes | Prior documentation-review snapshot | Section 1 methodology; Section 3 inventory; DOC-012, DOC-019, DOC-027; Section 7 |
| `docs/NOVICE_USABILITY_GUIDE.md` | 310 | Fully read: Yes | Canonical novice guide | Section 3 inventory; Section 4; DOC-004, DOC-006, DOC-007, DOC-009, DOC-011, DOC-012, DOC-020, DOC-024, DOC-026 |
| `docs/POCArchitect_Example_Report.md` | 311 | Fully read: Yes | Static illustrative report | Section 3 inventory; Section 7 |
| `docs/agentusage.md` | 81 | Fully read: Yes | Short usage orientation | Section 3 inventory; Section 6 duplication |
| `docs/architecture.md` | 81 | Fully read: Yes | Architecture reference | Section 3 inventory; Section 4; DOC-001, DOC-005, DOC-006, DOC-007, DOC-023; Section 8 |
| `docs/cli-reference.md` | 73 | Fully read: Yes | Generated CLI reference | Section 3 inventory; Section 4; DOC-002, DOC-003, DOC-023; Section 6/7 |
| `docs/command-guide.md` | 373 | Fully read: Yes | End-to-end command guide | Section 3 inventory; Section 4; DOC-001, DOC-002, DOC-003, DOC-006, DOC-008, DOC-010, DOC-015, DOC-016, DOC-018, DOC-020; Section 6 |
| `docs/configuration-reference.md` | 43 | Fully read: Yes | Generated configuration reference | Section 3 inventory; Section 4; DOC-003, DOC-004, DOC-017, DOC-021; Section 6/7 |
| `docs/docker-guide.md` | 134 | Fully read: Yes | Docker user guide | Section 3 inventory; Section 4; DOC-010, DOC-014; Section 6 |
| `docs/guides/LINUX_NOVICE_USABILITY_GUIDE.md` | 166 | Fully read: Yes | Linux/Bash novice supplement | Section 3 inventory; Section 4; DOC-020, DOC-021, DOC-026; Section 6 |
| `docs/guides/WINDOWS_NOVICE_USABILITY_GUIDE.md` | 166 | Fully read: Yes | Windows PowerShell novice supplement | Section 3 inventory; Section 4; DOC-004, DOC-020, DOC-021, DOC-026; Section 6 |
| `docs/ollama-setup-guide.md` | 81 | Fully read: Yes | Ollama/local-provider guide | Section 3 inventory; DOC-024, DOC-028 |
| `docs/ollama_preflight_check.py` | 134 | Fully read: Yes | Operator-facing Ollama check helper | Section 3 inventory; Section 4; DOC-024, DOC-028 |
| `example_usage/batch_urls.txt` | 2 | Fully read: Yes | Example batch input | Section 3 inventory; Section 4 examples; DOC-022 |
| `example_usage/single_url_example.md` | 1 | Fully read: Yes | Example single URL | Section 3 inventory; Section 4 examples |
| `example_usage/usage.md` | 11 | Fully read: Yes | Safe usage examples | Section 3 inventory; Section 4 examples |
| `pocarchitect/POC_Architect_Prompt.md` | 137 | Fully read: Yes | Packaged provider system prompt | Section 3 inventory; Section 4 outputs/providers; DOC-019, DOC-023; Section 7 |
| `pocarchitect/__init__.py` | 8 | Fully read: Yes | Package version initialization | Section 4 packaging/version |
| `pocarchitect/__main__.py` | 9 | Fully read: Yes | Module entry point | Section 4 entry points; DOC-001 |
| `pocarchitect/cli.py` | 931 | Fully read: Yes | Packaged CLI/runtime orchestration | Section 4 capability matrix; DOC-001 through DOC-012, DOC-014, DOC-021 through DOC-024; Section 6/8 |
| `pocarchitect/output.py` | 10 | Fully read: Yes | JSON event payload helper | Section 4 outputs/artifacts |
| `pocarchitect/preflight.py` | 233 | Fully read: Yes | Packaged preflight implementation | Section 4 preflight/configuration; DOC-001, DOC-004, DOC-005, DOC-015, DOC-020, DOC-021, DOC-024 |
| `pocarchitect/state.py` | 84 | Fully read: Yes | Batch-state implementation | Section 4 state/resume; DOC-011 |
| `preflight.py` | 161 | Fully read: Yes | Separate root preflight implementation | Section 4 entry points; DOC-001; Section 6 |
| `pyproject.toml` | 38 | Fully read: Yes | Package metadata and entry points | Section 4 packaging/defaults/platform; DOC-001, DOC-013, DOC-020 |
| `pytest.ini` | 26 | Fully read: Yes | Pytest defaults and marker metadata | Section 4 tests; DOC-025; Section 6 |
| `requirements-dev.txt` | 8 | Fully read: Yes | Development dependency declarations | Section 4 scripts/CI/tests |
| `requirements.txt` | 8 | Fully read: Yes | Runtime dependency declarations | Section 4 packaging/CI; DOC-024 |
| `scripts/apply_ci_fixes.py` | 204 | Fully read: Yes | CI compatibility patcher | Section 4 scripts; DOC-016; Section 6/7 |
| `scripts/apply_ci_fixes.template.py` | 242 | Fully read: Yes | Fallback patcher template | Section 4 scripts; DOC-016; Section 6 |
| `scripts/generate_docs.py` | 168 | Fully read: Yes | CLI/config reference generator | Section 4 scripts; DOC-017; Section 6/7 |
| `scripts/repair_apply_ci_fixes.py` | 100 | Fully read: Yes | Patcher repair utility | Section 4 scripts; DOC-016; Section 6 |
| `scripts/validate_documentation_links.py` | 76 | Fully read: Yes | Local Markdown link validator | Section 1 command results; Section 4; DOC-013, DOC-019; Section 8 |
| `scripts/validate_novice_guides.py` | 95 | Fully read: Yes | Novice-guide structure validator | Section 1 command results; Section 4; DOC-019, DOC-026; Section 6 |
| `test-full.sh` | 70 | Fully read: Yes | Real-provider Bash test script | Section 3 inventory; Section 4 scripts; DOC-008, DOC-015, DOC-022 |
| `tests/test_ci_fixes_script.py` | 12 | Fully read: Yes | Patcher source-integrity test | Section 4 tests; DOC-016 |
| `tests/test_cli.py` | 311 | Fully read: Yes | CLI/grounding/output/state tests | Section 4 tests; DOC-008, DOC-009, DOC-012 |
| `tests/test_dockerfile.py` | 19 | Fully read: Yes | Dockerfile ownership/order tests | Section 4 tests/Docker |
| `tests/test_documentation_links.py` | 16 | Fully read: Yes | Link-validator invocation test | Section 4 tests; DOC-019 |
| `tests/test_generate_docs.py` | 26 | Fully read: Yes | CLI generator test | Section 4 tests; DOC-017 |
| `tests/test_novice_guides.py` | 16 | Fully read: Yes | Novice-validator invocation test | Section 4 tests; DOC-019 |
| `tests/test_preflight.py` | 133 | Fully read: Yes | Preflight unit tests | Section 4 tests/preflight; DOC-024 |
| `tests/test_repair_apply_ci_fixes.py` | 107 | Fully read: Yes | Patcher-repair unit tests | Section 4 tests; DOC-016 |
| `verify.sh` | 72 | Fully read: Yes | Dry-run Bash verification script | Section 3 inventory; Section 4 scripts; DOC-009, DOC-015 |

## Appendix B. Claims explicitly not determinable from repository contents

These items were excluded from baseline findings except where the documentation's uncertainty or validation scope was itself the finding.

| Claim not determinable | Why repository text is insufficient | Boundary evidence |
|---|---|---|
| Current GitHub Actions jobs pass | The workflow defines intended jobs but contains no hosted-run record for current HEAD. | `.github/workflows/ci.yml:16-160`; historical pass wording is scoped to a prior review at `docs/DOCUMENTATION_REVIEW_REPORT.md:115-129`. |
| Current generated references exactly match generator output | The local `--check` could not import a declared runtime dependency, and no dependency was installed. | Generator imports the package app at `scripts/generate_docs.py:62-65`; the package imports OpenAI at `pocarchitect/cli.py:15-17`. |
| Any cloud provider currently accepts a named model, temperature, key, request, or price | The repository constructs SDK calls but does not contain provider service state, billing, or live responses. | `pocarchitect/cli.py:434-487`; docs explicitly leave provider-backed validation unrun at `docs/DOCUMENTATION_REVIEW_REPORT.md:127-129`. |
| External HTTP(S) documentation links currently resolve | The repository validator intentionally skips them. | `scripts/validate_documentation_links.py:46-49`. |
| The current Dockerfile builds/runs successfully on a particular Docker engine or Desktop release | Dockerfile and CI commands are static declarations; no current local build was run for this audit. | `Dockerfile:1-33`; `.github/workflows/ci.yml:125-136`; prior native-Desktop limitation at `docs/docker-guide.md:134`. |
| Clean-room Windows, Linux, or macOS installation succeeds | Repository instructions and Ubuntu workflow exist, but clean-machine state is external. | `docs/NOVICE_USABILITY_GUIDE.md:35-40`; `docs/NOVICE_USABILITY_GUIDE.md:275-277`. |
| A live Ollama service/model is available, private, performant, or sufficient for the prompt | Those properties belong to the external service, model, and host. | `docs/ollama-setup-guide.md:5-10`; `docs/ollama-setup-guide.md:72-81`. |
| Private GitHub repositories will or will not clone in every operator environment | The code supplies an unauthenticated HTTPS URL and disables terminal prompts, but ambient Git credential helpers/network state are external. | `pocarchitect/cli.py:261-283`; `pocarchitect/cli.py:310-328`; docs state private access is not configured by default at `docs/NOVICE_USABILITY_GUIDE.md:27-30`. |
| Maintainer intent for root `cli.py` and `preflight.py` | Packaging selection and divergence are explicit; intentional retention, deprecation, or deletion is not encoded in a current authoritative note. | `pyproject.toml:23-24`; `cli.py:23-50`; `preflight.py:14-21`; `pocarchitect/cli.py:27-109`. |
| A newly built wheel/sdist's complete file list or build success | Packaging policies are text evidence, but no artifact was built in this audit. DOC-013 is limited to the explicit README/include/prune declarations. | `pyproject.toml:31-38`; `MANIFEST.in:3-21`. |
| Provider-generated report accuracy, completeness, or safety | The repository supplies a prompt and selected source, while the response is external provider output. | `pocarchitect/POC_Architect_Prompt.md:40-137`; `README.md:3-5`; `docs/architecture.md:72-77`. |
| Exact contents of local `review-output/` | It is untracked/ignored and was intentionally excluded from the authoritative scope. | `.gitignore:24-25`; scope procedure in Section 1.1. |
| Exact Windows Python version(s) used in all prior manual checks | Tracked pages contain point-in-time statements but no raw run log that reconciles every check. | `docs/guides/WINDOWS_NOVICE_USABILITY_GUIDE.md:1-4`; `docs/DOCUMENTATION_REVIEW_REPORT.md:18-27`. |

## Appendix C. Independent baseline QA

A final read-only QA pass was performed after the baseline report assembly:

- Parsed 28 unique sequential finding IDs and confirmed every finding contains severity, category, both evidence fields, mismatch, audience, and correction.
- Recomputed severities from the finding bodies: Critical 0, High 9, Medium 13, Low 6; these equal the executive tables.
- Re-enumerated `git ls-files -z` and compared ordered ledger paths: 54 equals 54, with no missing or extra path; all 54 line counts match baseline bytes and all rows contain `Fully read: Yes`.
- Validated 404 baseline `path:line`/range citations against actual baseline line counts: zero out-of-range citations.
- Rechecked each evidence bullet for at least one tracked baseline citation and reread findings for language that asserted external behavior; uncertain external/runtime claims remain isolated in Appendix B.
- Re-ran `git status --short --untracked-files=all` for the audited repository: no output. The repository was not modified by the audit.
