# POCArchitect Linux Bash Supplement

Status: **PARTIALLY VERIFIED**. Ubuntu CI exercises Python 3.10-3.13, but a
clean Linux installation and provider-backed run have not been independently
validated.

> The repository-wide [Novice Usability Guide](../NOVICE_USABILITY_GUIDE.md) is
> authoritative for behavior, safety, providers, grounding, batch semantics,
> and troubleshooting. This supplement contains only Linux Bash and path
> differences plus a compact command ledger.

## Platform prerequisites

Use Bash with Git and Python 3.10 or newer. The repository does not enforce a
processor-architecture requirement. Check:

```bash
git --version
python3 --version
```

## Install and activate

```bash
git clone https://github.com/rikterskale/POCArchitect-AI-Agent.git
cd POCArchitect-AI-Agent
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[all]'
```

## Linux paths and safe output

The native default is `./reports`. An explicit report path is checked by both
standalone and automatic preflight:

```bash
python -m pocarchitect preflight --offline --output-dir ./my-reports
python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --output-dir ./my-reports
```

Use `./reports/batch_progress.json` for a Bash-relative ledger. Batch files may
contain blank lines and full-line `#` comments.

## Provider diagnostics

Real **cloud-provider** runs require only the key matching `xai`, `openai`, or
`groq`. A local provider needs no cloud key. Diagnose the provider that failed,
not the default xAI provider:

```bash
python -m pocarchitect preflight --provider openai
python -m pocarchitect preflight --provider local --base-url http://localhost:11434/v1
```

The local check requests only `/models`; it does not prove model suitability or
chat-completion behavior.

## Command ledger

| ID | Command | Safe expected result |
|---|---|---|
| LINUX-01 | `python -m pocarchitect --version` | Version is printed |
| LINUX-02 | `python -m pocarchitect preflight --offline --output-dir ./reports` | Installation, Git, and selected output path checks run without provider access |
| LINUX-03 | `python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --no-color` | No clone, automatic preflight, or provider call occurs |
| LINUX-04 | `python -m pocarchitect --format json --no-color batch-status --batch-state ./reports/batch_progress.json` | One JSON status event is emitted |
| LINUX-05 | `python -m pocarchitect --format json --no-color batch-reset --batch-state ./reports/batch_progress.json --yes` | Existing state is moved to a timestamped backup |

Run `deactivate` to leave the virtual environment. Keep reports and ledger
backups before removing `.venv` or the checkout.
