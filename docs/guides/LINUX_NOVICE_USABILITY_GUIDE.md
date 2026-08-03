# POCArchitect AI Agent — Linux Novice Guide

Status: **PARTIALLY VERIFIED**. The implementation is exercised in Ubuntu GitHub Actions, but a clean Linux installation was not run during this review.

## Before you begin

Use Bash on a supported Linux distribution. Install Git and Python 3.9+. Check them with `git --version` and `python3 --version`. This tool analyzes authorized GitHub PoC source with an LLM; it does not execute the retrieved PoC. Provider keys are secrets.

## Install

```bash
git clone https://github.com/rikterskale/POCArchitect-AI-Agent.git
cd POCArchitect-AI-Agent
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[all]'
```

Verify with `python -m pocarchitect --version` and `python -m pocarchitect preflight --offline`.

## Safest first run

```bash
python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run
```

Replace the example URL only with an authorized repository. This performs no clone and no provider call. Success is exit code 0 and a prompt panel.

## Provider setup and reports

Copy `.env.example` to `.env`, add one provider key, and confirm `.env` is ignored with `git check-ignore .env`. Normal runs require a provider key and write reports to `reports/`. Reports include source/provider/model metadata and a body hash. Review the secret warning before submitting source content.

## Batch, recovery, and cleanup

Use `python -m pocarchitect --batch example_usage/batch_urls.txt --batch-state ./reports/batch_progress.json`. Completed URLs are skipped on rerun; failed URLs remain retryable. Use `--output-dir` for a writable path. Press `Ctrl+C` to stop a foreground run, then run `deactivate`.

## Troubleshooting

| Symptom | Fix | Verify |
|---|---|---|
| `No API key found` | Use `--dry-run`, or configure the selected provider key in `.env` | `python -m pocarchitect preflight` |
| `ModuleNotFoundError` | Activate `.venv` and reinstall editable dependencies | `python -m pocarchitect --version` |
| Output permission error | Choose a directory you own with `--output-dir` | Repeat the dry run |
| Git ingestion failure | Confirm the URL is public/valid and retry with `--no-ingest` | Repeat the dry run |

See [`README.md`](../../README.md), [`docs/cli-reference.md`](../cli-reference.md), [`docs/configuration-reference.md`](../configuration-reference.md), and [`docs/docker-guide.md`](../docker-guide.md).
