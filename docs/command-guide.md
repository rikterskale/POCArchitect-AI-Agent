# POCArchitect Command Guide

This reference documents POCArchitect 0.2.0. Run commands from the repository
root and analyze only targets you are authorized to inspect. Never put provider
credentials on a command line or commit `.env`.

## Quick choices

| Goal | Command |
|---|---|
| Show CLI help | `python -m pocarchitect --help` |
| Verify installation without provider access | `python -m pocarchitect preflight --offline` |
| Verify a custom report path | `python -m pocarchitect preflight --offline --output-dir <PATH>` |
| Safely inspect a prompt | `python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run` |
| Analyze one authorized URL | `python -m pocarchitect --url <AUTHORIZED_URL> --provider <PROVIDER>` |
| Process a list with recovery state | `python -m pocarchitect --batch <FILE> --provider <PROVIDER>` |
| Inspect/reset state as JSON | `python -m pocarchitect --format json --no-color batch-status` / `batch-reset` |

Replace angle-bracket placeholders before use.

## Installation

### Windows PowerShell

```powershell
git clone https://github.com/rikterskale/POCArchitect-AI-Agent.git
Set-Location POCArchitect-AI-Agent
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[all]"
```

### macOS and Linux

```bash
git clone https://github.com/rikterskale/POCArchitect-AI-Agent.git
cd POCArchitect-AI-Agent
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[all]'
```

Python 3.10 or newer is required. Ubuntu CI covers Python 3.10-3.13. The macOS
path is documented but is not independently tested in current repository
evidence. The project does not enforce a processor-architecture requirement.

## Authoritative entry points

Use either:

```bash
pocarchitect --help
python -m pocarchitect --help
```

Both resolve to `pocarchitect.cli:app`. Runtime implementation lives only under
`pocarchitect/`; former root-level `cli.py` and `preflight.py` copies were
retired because they diverged from the packaged command.

## Preflight and dry-run boundaries

Offline preflight:

```bash
python -m pocarchitect preflight --offline --format json --no-color
```

It checks Python 3.10+, imports for `typer`, `rich`, `openai`, `dotenv`, and
`tenacity`, a runnable Git executable, the package command, the prompt asset,
and the resolved writable output path. It creates and removes only
`.write_test` inside that path.

Choose the exact path checked:

```bash
python -m pocarchitect preflight --offline --output-dir reports/client-a
```

A real main command resolves `--output-dir` before automatic preflight and
checks that same directory. Without an override, `/reports` is selected when
`/.dockerenv` exists or `IN_DOCKER` is set; otherwise `./reports` is used.

`--dry-run` bypasses **automatic preflight entirely**. It does not prove that
dependencies, Git, credentials, the prompt, or output writes are ready. Run the
standalone offline command above when those checks are needed.

Cloud-provider preflight checks the key for the selected provider:

```bash
python -m pocarchitect preflight --provider xai
python -m pocarchitect preflight --provider openai
python -m pocarchitect preflight --provider groq
```

Local preflight sends only an HTTP request to `<base-url>/models`:

```bash
python -m pocarchitect preflight --provider local --base-url http://localhost:11434/v1
```

It does not send the full prompt, test chat completions, prove that a named
model exists, or assess response quality and resource sufficiency.

## Single-URL workflows

### Safe no-clone preview

```bash
python -m pocarchitect --url https://github.com/example/poc \
  --no-ingest --dry-run --format json --no-color
```

This makes no clone or provider call, requires no credential, and writes no
report.

### Grounding preview without provider access

```bash
python -m pocarchitect --url <AUTHORIZED_GITHUB_URL> --dry-run --verbose
```

This can clone and read the public repository, but does not call a provider.
Because dry run bypasses preflight, run `preflight --offline` separately if
installation readiness also matters.

### Interactive real run

```bash
python -m pocarchitect --url <AUTHORIZED_GITHUB_URL> --provider openai
```

The tool previews redacted transfer content and asks for confirmation. Inspect
the preview for `WARNING: Ingestion failed`. A failed GitHub clone falls back to
warning/URL-only context and can still reach the provider after approval; cancel
unless URL-only analysis is acceptable. Successful report metadata records
`url-only-ingestion-failed`, not a successful clone.

For reviewed noninteractive automation, `--yes` bypasses confirmation. Use it
only after independently reviewing every authorized target and transfer.

## Main options and provider defaults

The generated [CLI Reference](cli-reference.md) is the complete option source.
`--risk-level` and `--target-os` accept free text. Mitigations are enabled; no
public negative mitigation switch exists.

| Provider | Required cloud setting | Default model |
|---|---|---|
| `xai` | `XAI_API_KEY` | `grok-3` |
| `openai` | `OPENAI_API_KEY` | `gpt-4o` |
| `groq` | `GROQ_API_KEY` | `llama-3.1-70b-versatile` |
| `local` | None | `qwen2.5-coder:32b` |

The current provider choices are exactly those four. Claude/Gemini wording in
the packaged prompt describes portability of the prompt text, not named CLI
providers. Configure another OpenAI-compatible service through
`--provider local --base-url <URL>`.

## Grounding selection

GitHub grounding uses a noninteractive depth-one, single-branch clone with a
90-second timeout. Selection is implementation-defined and bounded:

- candidates match one of the filename keywords or extensions listed in
  [Architecture](architecture.md#grounding-file-selection-rules);
- files over 250,000 bytes are skipped;
- each included file is truncated after 7,500 characters;
- only the first 25 matching readable files are included.

No source-completeness claim is made.

## Batch input, previews, recovery, and exit status

Batch input accepts one value per non-comment line. Blank lines and lines whose
trimmed content begins with `#` are ignored. Inline comments are **not** removed:

```text
# Authorized customer A targets
https://github.com/example/first-poc

https://github.com/example/second-poc
```

The checked-in `example_usage/batch_urls.txt` is a replacement template, not
billable input. `example_usage/dry_run_batch_urls.txt` is safe only with
`--no-ingest --dry-run`.

Preview every eligible item without network access:

```bash
python -m pocarchitect --batch example_usage/dry_run_batch_urls.txt \
  --no-ingest --dry-run --no-color
```

Dry run previews every non-resumed URL and does not write success records.

Run an authorized real batch:

```bash
python -m pocarchitect --batch <AUTHORIZED_BATCH_FILE> \
  --provider openai \
  --batch-state reports/customer-a-state.json
```

Processing continues after item failures so later URLs still run. After the
summary, the command exits:

| Exit | Meaning |
|---:|---|
| `0` | No processed batch item failed |
| `1` | One or more items failed; details were persisted and emitted |
| `2` | Invocation/input/state/confirmation error prevented normal processing |

Automation may gate on the nonzero exit and should retain the final
`batch_complete` event or ledger for item-level evidence.

### Version-2 batch ledger

```json
{
  "version": 2,
  "items": {
    "https://github.com/example/succeeded": {
      "status": "success",
      "updated_at": "2026-08-15T12:00:00+00:00"
    },
    "https://github.com/example/failed": {
      "status": "failed",
      "error": "sanitized failure text",
      "updated_at": "2026-08-15T12:01:00+00:00"
    }
  }
}
```

| Field | Contract |
|---|---|
| `version` | Must equal `2`; other versions are rejected without overwrite |
| `items` | Object keyed by the trimmed noncomment input value |
| `status` | Writer emits `success` or `failed`; summaries count other values as `unknown` |
| `updated_at` | UTC ISO-8601 timestamp written for current success/failure records |
| `error` | Sanitized message present for current failure records |

The loader guarantees only version 2 plus an object-valued `items` field; it
does not promise compatibility with arbitrary hand edits. For corrupt or
unsupported state, use the recoverable reset path:

```bash
python -m pocarchitect --format json --no-color \
  batch-reset --batch-state reports/customer-a-state.json --yes
```

The old file is moved to a timestamped `.bak` path.

## JSON Lines and global option placement

`--format` and `--no-color` are root options. Put them **before** a subcommand:

```bash
python -m pocarchitect --format json --no-color \
  batch-status --batch-state reports/customer-a-state.json
python -m pocarchitect --format json --no-color \
  batch-reset --batch-state reports/customer-a-state.json --yes
```

Each emits one object with at least `event` and `message`. `batch_status` also
includes `state_path`, `version`, `total`, `success`, `failed`, and `unknown`.
`batch_reset` includes `state_path` and, when a file existed, `backup_path`.

Main batch JSON output emits `batch_complete` with `total`, `processed`,
`success`, `failed`, `skipped`, `resumed`, and `state_path`.

## Report files and provenance

Successful real runs write
`POCAnalysis_<slug>_<UTC timestamp>.md`. Front matter contains:

| Field | Meaning |
|---|---|
| `project` | Fixed project name |
| `source_url` | Operator-supplied URL |
| `provider`, `model` | Selected provider/model |
| `prompt_asset` | Packaged prompt path |
| `generated_at` | UTC ISO-8601 timestamp |
| `ingestion` | `disabled`, `url-only-non-github`, `url-only-ingestion-failed`, or `github-shallow-clone` |
| `grounding_files_selected` | Number of source files included; zero for URL-only/disabled |
| `content_sha256` | SHA-256 of the provider response body |

The ingestion value records the actual control-path outcome. It does not prove
provider response accuracy or source completeness.

## Docker

Build and safe-preview commands:

```bash
docker build -t pocarchitect:latest .
docker run --rm pocarchitect:latest \
  --url https://github.com/example/poc --no-ingest --dry-run --no-color
```

Real grounded runs require `-it` for confirmation or reviewed `--yes`
automation. See the [Docker Guide](docker-guide.md).

## Match CI locally

Install developer dependencies, then run the quality/documentation controls:

```bash
python -m pip install -r requirements-dev.txt
ruff check --output-format=github .
ruff format --check .
black --check --diff .
mypy pocarchitect tests
python scripts/generate_docs.py --check
python scripts/validate_novice_guides.py
python scripts/validate_documentation_links.py
python scripts/validate_documentation_commands.py
python scripts/validate_documentation_reports.py
python scripts/validate_ci_workflow.py
```

Run the test/security/build equivalents:

```bash
pytest --cov=pocarchitect --cov-report=xml
pip-audit
docker build -t pocarchitect:test .
docker run --rm pocarchitect:test --help
python -m build
python scripts/validate_distribution.py dist
```

CI repeats tests on Python 3.10-3.13. Codecov upload and hosted runner outcomes
are CI-only; local command success does not prove those services succeed.

Documentation controls have intentionally bounded claims:

| Control | What it checks | What it does not prove |
|---|---|---|
| `generate_docs.py --check` | Checked-in text equals generator output | Explanatory policy is behaviorally accurate |
| `validate_novice_guides.py` | Required headings, platform deltas, and ledgers | Every command behaves correctly |
| `validate_documentation_links.py` | Local Markdown targets and anchors | External URL reachability or prose accuracy |
| `validate_documentation_commands.py` | Explicit no-network command probes | Commands outside its listed probe set |
| `validate_documentation_reports.py` | Report structure, closure evidence ranges/fingerprint, historical banner | Behavioral truth of cited code |
| `validate_ci_workflow.py` | Required checked-in CI invariants and absence of retired mutators | Hosted CI success |
| `validate_distribution.py` | Local Markdown targets inside the built sdist | External links or wheel-installed docs |

The former `apply_ci_fixes.py`, its embedded template, and
`repair_apply_ci_fixes.py` were removed because they could overwrite the
canonical multi-job workflow. `.github/workflows/ci.yml` is the sole workflow
source of truth; no tracked script rewrites it.

## Repository shell scripts

```bash
./verify.sh
./test-full.sh <authorized-real-batch-file>
```

`verify.sh` uses `preflight --offline` and no-network dry runs.
`test-full.sh` uses `preflight --provider openai`, makes billable OpenAI calls,
requires an explicit authorized batch file, and refuses repository placeholder
fixtures. It uses `set -e`; batch item failures now produce exit 1 after all
items are attempted.

## Troubleshooting

| Symptom | Action |
|---|---|
| Command unavailable | Activate `.venv` or use `python -m pocarchitect --help` |
| Credential rejected | Run preflight with the **same** `--provider`; do not print the key |
| Local endpoint unavailable | Repeat local preflight with the same `--base-url`; remember it tests only `/models` |
| Output permission failure | Pass the intended path to both `preflight --offline --output-dir` and the real command |
| Clone warning in preview | Cancel, correct URL/network/public access, and retry; approve only if URL-only analysis is acceptable |
| Batch exit 1 | Inspect `batch_complete.failed`, `batch-status`, and failed ledger entries |
| Unsupported/corrupt state | Run `batch-reset --yes` and retain the printed backup |
| No report | Dry runs write none; real reports require a successful provider response |

For metadata-derived details, see [CLI Reference](cli-reference.md),
[Configuration Reference](configuration-reference.md), and
[Architecture](architecture.md).
