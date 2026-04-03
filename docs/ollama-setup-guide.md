# Ollama Setup Guide for POCArchitect (April 2026)

This guide helps you run **completely local** LLMs with POCArchitect — no cloud API keys required.

## Why Use Ollama with POCArchitect?
- 100% private (nothing leaves your machine)
- Zero refusals on exploit code or red-team techniques
- Works perfectly with `--provider local`

## 1. Install Ollama
- **Windows**: Download and run the installer from https://ollama.com/download
- **macOS**: `brew install ollama` or download from the website
- **Linux**: `curl -fsSL https://ollama.com/install.sh | sh`

Verify:

```bash
ollama --version
```

## 2. Start the Ollama Server
Keep this running in a separate terminal:

```bash
ollama serve
```

## 3. Recommended Models (Best for PoC Analysis)

```bash
# Best overall for exploit writing & code analysis (recommended)
ollama pull qwen2.5-coder:32b

# Faster alternative (still very capable)
ollama pull qwen2.5-coder:14b

# Strong reasoning model
ollama pull deepseek-r1:32b
```

## 4. Test Ollama (Recommended)
Run the included preflight checker:

```bash
python docs/ollama_preflight_check.py
```

This validates the server, model, and OpenAI-compatible endpoint that POCArchitect actually uses.

## 5. Run POCArchitect with Local Ollama

```bash
pocarchitect --url https://github.com/example/poc-repo \
  --provider local \
  --base-url http://localhost:11434/v1 \
  --model qwen2.5-coder:32b
```

You can combine with any other flags:

```bash
--dry-run --verbose --risk-level Critical --target-os Windows --no-ingest
```

## Common Issues & Fixes

| Issue | Fix |
|---|---|
| Connection refused | Run `ollama serve` in another terminal |
| Model not found | Run `ollama pull <model>` |
| Out of memory | Use the 14b version or add `--num-gpu 0` |
| Slow generation | Use quantized model (`qwen2.5-coder:14b-q4_K_M`) |

You are now ready to run fully local, uncensored PoC analysis.

**Last Updated:** April 03, 2026