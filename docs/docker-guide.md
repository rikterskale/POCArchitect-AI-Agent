# Docker Guide - POCArchitect AI Agent

This guide covers the repository Dockerfile reviewed with POCArchitect 0.2.0. The image uses Python 3.12, installs Git for GitHub grounding, runs as the non-root `pocuser` user, and exposes `/reports` as a writable volume.

## Prerequisites

- Docker installed and running
- An authorized public GitHub repository URL for any real grounding run
- A provider credential in a local `.env` file for cloud-provider runs, or a reachable local OpenAI-compatible endpoint
- A writable host folder to mount at `/reports` when a report should be retained

---

## 1. Build the Docker Image

```bash
docker build -t pocarchitect:latest .
```

The Dockerfile uses a multi-stage build and runs the final container as the non-root `pocuser` user. Image size is not asserted because it varies by Docker platform and cache state.

---

## 2. Run POCArchitect in Docker

### Show Help

```bash
docker run --rm pocarchitect:latest --help
```

PowerShell uses the same help command:

```powershell
docker run --rm pocarchitect:latest --help
```

### Safe first run

Run this from the repository root after building the image:

```bash
docker run --rm pocarchitect:latest \
  --url https://github.com/example/poc \
  --no-ingest --dry-run --no-color
```

This does not clone the URL, call a provider, require a key, or write a report. A successful run prints `DRY RUN MODE` and the prompt.

### Credential-free report smoke test

This exercises the container's provider boundary and verifies that the report
volume is usable without a cloud credential:

```bash
docker volume create pocarchitect-smoke
docker run --rm \
  -v pocarchitect-smoke:/reports \
  pocarchitect:latest \
  --format json --no-color demo
docker run --rm \
  --entrypoint python \
  -v pocarchitect-smoke:/reports \
  pocarchitect:latest \
  -c "from pathlib import Path; assert list(Path('/reports/demo').glob('*.md'))"
```

PowerShell:

```powershell
docker run --rm pocarchitect:latest `
  --url https://github.com/example/poc `
  --no-ingest --dry-run --no-color
```

### Interactive cloud-provider run

Use an interactive terminal so POCArchitect can display the source-transfer preview and ask for confirmation. Replace `<AUTHORIZED_GITHUB_URL>` with a public repository you are allowed to inspect.

```bash
docker run --rm -it \
  -v "$(pwd)/reports:/reports" \
  --env-file .env \
  pocarchitect:latest \
  --url <AUTHORIZED_GITHUB_URL> --provider xai
```

The command creates a report in the mounted host `reports/` folder only after the provider call succeeds. Do not put a provider key directly on a command line; `--env-file .env` keeps it out of shell history.

On PowerShell, use `${PWD}` for the current directory:

```powershell
docker run --rm -it `
  -v "${PWD}\reports:/reports" `
  --env-file .env `
  pocarchitect:latest `
  --url <AUTHORIZED_GITHUB_URL> --provider xai
```

### Using a `.env` File (Cleanest)

```bash
docker run --rm -it \
  --env-file .env \
  -v "$(pwd)/reports:/reports" \
  pocarchitect:latest \
  --url <AUTHORIZED_GITHUB_URL> --provider xai
```

### Batch Mode

```bash
docker run --rm -it \
  --env-file .env \
  -v "$(pwd)/reports:/reports" \
  -v "$(pwd)/batch_urls.txt:/batch_urls.txt" \
  pocarchitect:latest \
  --batch /batch_urls.txt
```

Each nonblank, noncomment line is treated as one input. Full-line `#` comments
and blank lines are ignored; inline comments are not removed. The container asks
for a source-transfer confirmation for each item. Add `--yes` only to a
noninteractive job whose URLs and transfer are already authorized and reviewed.
If any item fails, processing continues and the container exits 1 after the
batch summary.

### Full Example with Custom Options

```bash
docker run --rm -it \
  --env-file .env \
  -v "$(pwd)/reports:/reports" \
  pocarchitect:latest \
  --url <AUTHORIZED_GITHUB_URL> \
  --provider xai \
  --model grok-3 \
  --output-dir /reports \
  --verbose
```

---

## 3. Environment Variables

| Variable | Description | Required |
|---|---|---|
| `XAI_API_KEY` | xAI / Grok key | Yes* |
| `OPENAI_API_KEY` | OpenAI key | Yes* |
| `GROQ_API_KEY` | Groq key | Yes* |

*Only the key for the provider you choose is required.

---

## 4. Tips & Best Practices

- Mount `-v "$(pwd)/reports:/reports"` whenever you want reports or batch state retained on the host. The container default output is `/reports`.
- Use `--rm` to auto-clean the container after it finishes.
- Create an **interactive real-run** alias:

```bash
alias pocarch='docker run --rm -it --env-file .env -v "$(pwd)/reports:/reports" pocarchitect:latest'
```

Then run: `pocarch --url <AUTHORIZED_GITHUB_URL> --provider <provider>`. The
`-it` flag is required for the default confirmation path.

For a no-interaction, no-provider-call preview alias:

```bash
alias pocarch-preview='docker run --rm -v "$(pwd)/reports:/reports" pocarchitect:latest'
pocarch-preview --url https://github.com/example/poc --no-ingest --dry-run --no-color
```

- GitHub grounding uses an unauthenticated shallow Git clone. It is intended for public GitHub repositories; do not assume private repository access is configured in this image.

---

## 5. Troubleshooting

- **"Permission denied" on reports** → The container runs as non-root `pocuser`. Create a host `reports` folder you can write to, mount it at `/reports`, then repeat the safe dry run before a real run.
- **Git clone fails** → Confirm the URL is a public GitHub repository and that the container has network access. To validate the CLI without cloning, repeat the command with `--no-ingest --dry-run`.
- **API key not found** → Check that `.env` is in the directory where you run Docker and contains the key matching `--provider`; then rerun preflight with that same provider, for example `docker run --rm --env-file .env pocarchitect:latest preflight --provider openai`.
- **Help fails when captured on Windows** → Use the current image and put global options before the command, for example `docker run --rm pocarchitect:latest --format json --no-color demo`. Native Windows CLI help is rendered as plain text for safe redirection.
- **Rebuild after changes** → `docker build --no-cache -t pocarchitect:latest .`

---

**Validation status:** Docker build and `docker run --rm pocarchitect:test --help` are exercised by CI on Ubuntu. Native Docker Desktop runs and provider-backed runs were not executed during this documentation review.
