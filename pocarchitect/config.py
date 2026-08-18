"""Shared runtime configuration used by the CLI, preflight, and documentation."""

from __future__ import annotations

import os
from pathlib import Path

PROVIDER_KEY_NAMES = {
    "xai": "XAI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "groq": "GROQ_API_KEY",
}

DEFAULT_MODELS = {
    "xai": "grok-3",
    "openai": "gpt-4o",
    "groq": "llama-3.1-70b-versatile",
    # Keep the default practical for a developer laptop. Larger models remain
    # available through an explicit --model selection.
    "local": "qwen2.5-coder:14b",
}

DEFAULT_PROVIDER = "xai"
DEFAULT_LOCAL_BASE_URL = "http://localhost:11434/v1"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_RISK_LEVEL = "High"
DEFAULT_TARGET_OS = "Linux"

# Bounded limits for untrusted repository ingestion and provider calls.
MAX_CLONE_SECONDS = 90
MAX_GROUNDING_FILES = 25
MAX_GROUNDING_FILE_BYTES = 250_000
MAX_GROUNDING_TOTAL_BYTES = 5_000_000
MAX_REPOSITORY_FILES_SCANNED = 20_000
MAX_GROUNDING_CHARACTERS = 180_000
MAX_PROMPT_CHARACTERS = 500_000
MAX_PROVIDER_ATTEMPTS = 3
MAX_OUTPUT_TOKENS = 8_192


def default_output_dir(cwd: Path | None = None) -> Path:
    """Return the report path used when the operator does not provide one."""
    if Path("/.dockerenv").exists() or os.getenv("IN_DOCKER"):
        return Path("/reports")
    return (cwd or Path.cwd()) / "reports"
