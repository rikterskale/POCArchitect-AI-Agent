# POCArchitect AI Agent — Windows Novice Guide

Status: **PARTIALLY VERIFIED**. The CLI was verified with Python 3.12 on Windows; native clean-room, Docker, and provider-backed runs require local validation.

> Begin with the repository-wide [Novice Usability Guide](../NOVICE_USABILITY_GUIDE.md). This page remains a Windows PowerShell supplement and command ledger.

## Before you begin

Use Windows Terminal with PowerShell. Install Git and Python 3.10+. Check them with `git --version` and `py --version`. This tool analyzes authorized GitHub PoC source with an LLM; it does not execute the retrieved PoC. Provider keys are secrets.

## Install

```powershell
git clone https://github.com/rikterskale/POCArchitect-AI-Agent.git
Set-Location .\POCArchitect-AI-Agent
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[all]"
```

If activation is blocked, use `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` for the current terminal only. Verify with `python -m pocarchitect --version` and `python -m pocarchitect preflight --offline`.

## Safest first run

```powershell
python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run
```

Replace the example URL only with an authorized repository. This performs no clone and no provider call. Success is exit code 0 and a prompt panel.

## Provider setup and reports

Copy `.env.example` to `.env`, add one provider key, and confirm `.env` is ignored with `git check-ignore .env`. Normal runs require a provider key and write reports to `reports\`. Reports include source/provider/model metadata and a body hash. Review the secret warning before submitting source content.

## Batch, recovery, and cleanup

Use `python -m pocarchitect --batch example_usage\batch_urls.txt --batch-state .\reports\batch_progress.json`. Completed URLs are skipped on rerun; failed URLs remain retryable. Use `--output-dir` for a writable path. Press `Ctrl+C` to stop a foreground run, then run `deactivate`.

## Troubleshooting

| Symptom | Fix | Verify |
|---|---|---|
| `No API key found` | Use `--dry-run`, or configure the selected provider key in `.env` | `python -m pocarchitect preflight` |
| `ModuleNotFoundError` | Activate `.venv` and reinstall editable dependencies | `python -m pocarchitect --version` |
| Output permission error | Choose a folder you own with `--output-dir` | Repeat the dry run |
| Git ingestion failure | Confirm the URL is public/valid and retry with `--no-ingest` | Repeat the dry run |

See [`README.md`](../../README.md), [`docs/cli-reference.md`](../cli-reference.md), [`docs/configuration-reference.md`](../configuration-reference.md), and [`docs/docker-guide.md`](../docker-guide.md).

## Scope and safety

Only analyze repositories you are authorized to inspect. POCArchitect clones source but does not execute retrieved PoC code.

## Supported environment

Use 64-bit Windows with PowerShell, Git, and Python 3.10 or newer. Docker is optional.

## Prepare a workspace

Work in a folder you own, such as `C:\Users\<you>\source`, so report and batch-state files are writable.

## Create the virtual environment

Run `py -m venv .venv` once per checkout. Do not install project dependencies globally.

## Activate the environment

Run `./.venv/Scripts/Activate.ps1` in every new PowerShell session before using the project.

## Install the package

Use `python -m pip install -e ".[all]"` from the checkout. Re-run it after pulling dependency changes.

## Verify the command

Run `python -m pocarchitect --version`. A version event or plain version string confirms the package entry point works.

## Verify dependencies

Run `python -m pocarchitect preflight --offline`. Offline preflight checks the installation without a credential or endpoint call.

## Choose a report directory

The default is `reports\`. Set `--output-dir .\my-reports` when you need a different writable location.

## Configure a cloud provider

Copy `.env.example` to `.env` and add only the key for `--provider xai`, `openai`, or `groq`. Never paste a key into a command line.

## Configure a local provider

Local OpenAI-compatible providers use `http://localhost:11434/v1` by default and require no cloud key. Check a running local service with `python -m pocarchitect preflight --provider local`.

## Run provider-aware preflight

Use the same `--provider` and, for a custom local endpoint, `--base-url` that you will use for a report. The check explains the selected prerequisite only.

## Review ingestion consent

Before a real ingestion, POCArchitect shows the provider, model, source classification, redaction count, and size estimate. Decline to cancel before any source is sent.

## Use noninteractive automation

For a reviewed, authorized job, add `--yes` to approve the displayed transfer without a prompt. Noninteractive source ingestion fails safely without it.

## Use accessible text output

Add `--no-color` for terminals, logs, and screen readers that should not receive ANSI styling.

## Use JSON Lines output

Add `--format json` when another tool consumes results. Each output line is a JSON event with an `event` and `message` field.

## Start a batch

Use `python -m pocarchitect --batch example_usage\batch_urls.txt --yes` only for authorized URLs. The default ledger is `reports\batch_progress.json`.

## Inspect batch progress

Run `python -m pocarchitect batch-status --batch-state .\reports\batch_progress.json` to see completed, failed, and unknown entries before resuming.

## Reset batch progress

Run `python -m pocarchitect batch-reset --batch-state .\reports\batch_progress.json --yes` to start over. The previous ledger is moved to a timestamped backup.

## Recover from interruption

Rerun the same batch command. Atomic ledger writes preserve prior successful entries, which are skipped on resume.

## Fix local endpoint errors

Start the local provider, verify its OpenAI-compatible `/models` endpoint, and pass `--base-url` if it is not the default.

## Fix credential errors

Check the selected provider name and its matching `.env` variable. Do not print the value while troubleshooting.

## Fix Git ingestion errors

Confirm the repository URL is public and authorized. Use `--no-ingest --dry-run` to verify the rest of the workflow without cloning.

## Fix permission errors

Choose an `--output-dir` under your user profile and ensure no other process locks its batch-state file.

## Update the project

Run `git pull`, activate `.venv`, then run `python -m pip install -e ".[all]"` and the offline preflight again.

## Clean up

Run `deactivate`, delete reports only after retaining what you need, and remove `.venv` only when you no longer need the checkout.

## Get help

Run `python -m pocarchitect --help`, `python -m pocarchitect preflight --help`, or read [`docs/cli-reference.md`](../cli-reference.md).

## Command ledger

| ID | Command | Safe expected result |
|---|---|---|
| WIN-01 | `python -m pocarchitect --version` | Version is printed |
| WIN-02 | `python -m pocarchitect preflight --offline` | Installation checks pass without credentials |
| WIN-03 | `python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --no-color` | No clone or provider call occurs |
| WIN-04 | `python -m pocarchitect batch-status --batch-state .\reports\batch_progress.json` | Resume state is summarized |
| WIN-05 | `python -m pocarchitect batch-reset --batch-state .\reports\batch_progress.json --yes` | Prior state is backed up |
