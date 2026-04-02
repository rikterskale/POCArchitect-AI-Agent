# Docker Guide - POCArchitect-AI-Agent

This guide explains how to build, run, and use **POCArchitect** inside Docker.

## Prerequisites

- Docker installed and running
- API key for your preferred LLM provider (recommended: Grok/xAI)
- (Optional) GitHub token if fetching private repositories

## 1. Clone the repo (do this once, or git pull when you want updates)
- git clone https://github.com/rikterskale/POCArchitect-AI-Agent.git
- cd POCArchitect-AI-Agent

## 2. Build the Docker image
- docker build -t pocarchitect:latest .
```

## 2. Run POCArchitect in Docker

### Basic Usage (Show Help)

```bash
docker run --rm pocarchitect --help
```

### Single URL Mode

```bash
docker run --rm \
  -e GROK_API_KEY=your_grok_api_key_here \
  -v $(pwd)/reports:/app/reports \
  pocarchitect \
  --url https://github.com/example/poc-repo
```

### Batch Mode

```bash
docker run --rm \
  -e GROK_API_KEY=your_grok_api_key_here \
  -v $(pwd)/reports:/app/reports \
  pocarchitect \
  --batch /app/pocs.txt
```

**Note:** When using `--batch`, you need to mount your batch file as well.

### Full Batch Example

```bash
docker run --rm \
  -e GROK_API_KEY=your_grok_api_key_here \
  -v $(pwd)/reports:/app/reports \
  -v $(pwd)/pocs.txt:/app/pocs.txt \
  pocarchitect \
  --batch /app/pocs.txt
```

## 3. Common Usage Examples

### Using OpenAI instead of xAI

```bash
docker run --rm \
  -e OPENAI_API_KEY=sk-your_openai_key \
  -v $(pwd)/reports:/app/reports \
  pocarchitect \
  --url https://github.com/example/poc \
  --provider openai \
  --model gpt-4o
```

### Running with Verbose Output

```bash
docker run --rm \
  -e GROK_API_KEY=your_key \
  -v $(pwd)/reports:/app/reports \
  pocarchitect \
  --url https://github.com/example/poc \
  --verbose
```

### Using a Different Output Directory

```bash
docker run --rm \
  -e GROK_API_KEY=your_key \
  -v $(pwd)/my_custom_reports:/app/reports \
  pocarchitect \
  --url https://github.com/example/poc
```

## 4. Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| GROK_API_KEY | API key for xAI Grok | Yes* |
| OPENAI_API_KEY | API key for OpenAI | Yes* |
| ANTHROPIC_API_KEY | API key for Claude | Yes* |
| GEMINI_API_KEY | API key for Google Gemini | Yes* |

*Only the key for the provider you are using is required.

## 5. Tips & Best Practices

- Always mount a volume (`-v`) for `/app/reports` so generated reports persist on your host machine.
- Use `--rm` flag to automatically clean up the container after it finishes.
- For frequent use, consider creating an alias or a shell script.
- If you frequently use the same API key, you can add it to a `.env` file and use `docker run --env-file .env ...`

### Example Shell Alias

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
alias pocarch='docker run --rm \
  -e GROK_API_KEY=$GROK_API_KEY \
  -v $(pwd)/reports:/app/reports \
  pocarchitect'
```

Then use simply:

```bash
pocarch --url https://github.com/user/repo
```

## 6. Troubleshooting

- **"API key not found"** → Make sure you pass the correct environment variable.
- **Permission issues** → The container runs as a non-root user. Make sure your mounted `reports/` folder is writable.
- **Git clone fails** → For private repos, mount your SSH keys or use a GitHub token.
- **Image too large** → Use `docker build --no-cache .` after making changes.

---

Last Updated: April 2026
