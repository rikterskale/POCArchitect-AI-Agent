# Docker Guide - POCArchitect AI Agent

This guide explains how to build, run, and use **POCArchitect** inside Docker (v0.2.0+).

## Prerequisites

- Docker installed and running
- API key for your preferred LLM provider (xAI/Grok recommended)
- (Optional) `.env` file with your keys

---

## 1. Build the Docker Image

```bash
docker build -t pocarchitect:latest .
```

This uses a multi-stage build → final image is ~180–220 MB and runs as non-root user.

---

## 2. Run POCArchitect in Docker

### Show Help

```bash
docker run --rm pocarchitect --help
```

### Single URL Mode (Recommended)

```bash
docker run --rm \
  -v "$(pwd)/reports:/reports" \
  -e XAI_API_KEY=your_xai_key_here \
  pocarchitect \
  --url https://github.com/example/poc-repo
```

### Using a `.env` File (Cleanest)

```bash
docker run --rm \
  --env-file .env \
  -v "$(pwd)/reports:/reports" \
  pocarchitect \
  --url https://github.com/example/poc-repo
```

### Batch Mode

```bash
docker run --rm \
  --env-file .env \
  -v "$(pwd)/reports:/reports" \
  -v "$(pwd)/batch_urls.txt:/batch_urls.txt" \
  pocarchitect \
  --url /batch_urls.txt
```

### Full Example with Custom Options

```bash
docker run --rm \
  --env-file .env \
  -v "$(pwd)/reports:/reports" \
  pocarchitect \
  --url https://github.com/example/poc-repo \
  --provider xai \
  --model grok-4 \
  --output-dir /reports \
  --verbose
```

---

## 3. Environment Variables

| Variable | Description | Required |
|---|---|---|
| `XAI_API_KEY` | xAI / Grok key | Yes* |
| `OPENAI_API_KEY` | OpenAI / Groq key | Yes* |
| `ANTHROPIC_API_KEY` | Anthropic (Claude) key | Yes* |
| `GEMINI_API_KEY` | Google Gemini key | Yes* |

*Only the key for the provider you choose is required.

---

## 4. Tips & Best Practices

- Always mount `-v "$(pwd)/reports:/reports"` — reports are written to this volume.
- Use `--rm` to auto-clean the container after it finishes.
- Create a shell alias for daily use:

```bash
alias pocarch='docker run --rm --env-file .env -v "$(pwd)/reports:/reports" pocarchitect'
```

Then just run: `pocarch --url <url>`

- Python-side PoC ingestion (grounding context) works automatically inside Docker — no extra setup needed.
- For private GitHub repos, pass a GitHub token via `--github-token` (CLI support coming in next release).

---

## 5. Troubleshooting

- **"Permission denied" on reports** → The container runs as non-root `pocuser`. Make sure your host `./reports` folder is writable (`chmod 777 reports` or `mkdir -p reports`).
- **Git clone fails** → Public repos work out of the box. Private repos need a token (future CLI flag).
- **API key not found** → Use `--env-file .env` or explicit `-e KEY=...`.
- **Rebuild after changes** → `docker build --no-cache -t pocarchitect:latest .`

---

*Last Updated: April 2026 (matches Dockerfile v0.2.0)*
