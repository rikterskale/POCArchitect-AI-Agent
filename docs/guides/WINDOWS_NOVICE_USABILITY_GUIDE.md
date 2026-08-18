# POCArchitect Windows PowerShell Supplement

Status: **PARTIALLY VERIFIED**. CI clean-installs the wheel and runs the offline
readiness gate on Windows/Python 3.12. Interactive PowerShell setup,
provider-backed operation, WSL/Git Bash, and Docker Desktop remain outside that
gate.

> The repository-wide [Novice Usability Guide](../NOVICE_USABILITY_GUIDE.md) is
> authoritative for behavior, safety, providers, grounding, batch semantics,
> and troubleshooting. This supplement contains only Windows PowerShell and path
> differences plus a compact command ledger.

## Platform prerequisites

Use Windows PowerShell in Windows Terminal with Git and Python 3.10 or newer.
The repository does not enforce a processor-architecture requirement. Check:

```powershell
git --version
py --version
```

## Install and activate

```powershell
git clone https://github.com/rikterskale/POCArchitect-AI-Agent.git
Set-Location .\POCArchitect-AI-Agent
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[all]"
```

If activation is blocked, set policy for the current process only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Windows paths and safe output

The native default is `.\reports`. An explicit report path is checked by both
standalone and automatic preflight:

```powershell
python -m pocarchitect preflight --offline --output-dir .\my-reports
python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --output-dir .\my-reports
```

Use `.\reports\batch_progress.json` for a PowerShell-relative ledger. Batch
files may contain blank lines and full-line `#` comments.

## Provider diagnostics

Real **cloud-provider** runs require only the key matching `xai`, `openai`, or
`groq`. A local provider needs no cloud key. Diagnose the provider that failed,
not the default xAI provider:

```powershell
python -m pocarchitect preflight --provider openai
python -m pocarchitect preflight --provider local --base-url http://localhost:11434/v1
```

The local check requests only `/models`; it does not prove model suitability or
chat-completion behavior.

## Command ledger

| ID | Command | Safe expected result |
|---|---|---|
| WIN-01 | `python -m pocarchitect --version` | Version is printed |
| WIN-02 | `python -m pocarchitect preflight --offline --output-dir .\reports` | Installation, Git, and selected output path checks run without provider access |
| WIN-03 | `python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --no-color` | No clone, automatic preflight, or provider call occurs |
| WIN-04 | `python -m pocarchitect --format json --no-color batch-status --batch-state .\reports\batch_progress.json` | One JSON status event is emitted |
| WIN-05 | `python -m pocarchitect --format json --no-color batch-reset --batch-state .\reports\batch_progress.json --yes` | Existing state is moved to a timestamped backup |

Run `deactivate` to leave the virtual environment. Keep reports and ledger
backups before removing `.venv` or the checkout.
