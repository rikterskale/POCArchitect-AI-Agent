# Ollama Setup Guide for POCArchitect

This guide explains how to use Ollama as POCArchitect's `local` provider. The CLI works with any reachable OpenAI-compatible local endpoint; Ollama is one option. A local provider does not require a cloud-provider key, but GitHub grounding still needs network access when `--no-ingest` is not used.

## Scope and limitations

- POCArchitect uses `http://localhost:11434/v1` as the default local endpoint.
- The CLI does not install, start, or select an Ollama model for you.
- Local-provider behavior, data handling, and model responses are controlled by your local service and model; POCArchitect makes no privacy or response-guarantee claim.

## 1. Install Ollama
- **Windows**: Download and run the installer from https://ollama.com/download
- **macOS and Linux**: use an installation method published by Ollama for your operating system.

Verify:

```bash
ollama --version
```

## 2. Start the Ollama Server
Keep this running in a separate terminal:

```bash
ollama serve
```

## 3. Choose a model

```bash
# The POCArchitect default model name for --provider local.
ollama pull qwen2.5-coder:32b

# Alternative model names must be passed with --model.
ollama pull qwen2.5-coder:14b
```

> **Note:** The included preflight checker (`docs/ollama_preflight_check.py`) tests for `qwen2.5-coder:32b` by default. If you use a different model, update the `TEST_MODEL` variable in that script to match.

## 4. Test Ollama
Run the included preflight checker:

```bash
python docs/ollama_preflight_check.py
```

This helper validates the server, the `qwen2.5-coder:32b` model name, and the OpenAI-compatible endpoint (`/v1/chat/completions`) that POCArchitect uses. It sends a short local test request and therefore may use local compute.

> **Prerequisite:** The checker requires the `requests` library. Install it with `pip install requests` if not already available.

Before a real run, check the same endpoint through POCArchitect:

```bash
python -m pocarchitect preflight --provider local --base-url http://localhost:11434/v1
```

## 5. Run POCArchitect with Local Ollama

```bash
python -m pocarchitect --url https://github.com/example/poc-repo \
  --provider local \
  --base-url http://localhost:11434/v1 \
  --model qwen2.5-coder:32b
```

Run this in an interactive terminal. POCArchitect shows a redacted source-transfer preview before it sends any selected GitHub source to the local endpoint. Use `--no-ingest --dry-run` first if you only want to inspect the prompt.

You can combine with any other flags:

`--dry-run`, `--verbose`, `--risk-level`, `--target-os`, and `--no-ingest` can be combined with the command. `--dry-run --no-ingest` is the safe, no-provider-call combination.

## Common Issues & Fixes

| Issue | Fix |
|---|---|
| Connection refused | Run `ollama serve` in another terminal |
| Model not found | Run `ollama pull <model>` |
| Out of memory | Choose and pull a smaller model in Ollama, then pass its exact name with `--model` |
| Slow generation | Choose a model appropriate for the local hardware; POCArchitect has no performance-control flag for Ollama |

**Validation status:** The POCArchitect local-endpoint preflight behavior is covered by tests. Ollama installation, model download, and a live local endpoint were not run during this documentation review.
