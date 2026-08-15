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
    "local": "qwen2.5-coder:32b",
}

DEFAULT_PROVIDER = "xai"
DEFAULT_LOCAL_BASE_URL = "http://localhost:11434/v1"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_RISK_LEVEL = "High"
DEFAULT_TARGET_OS = "Linux"


def default_output_dir(cwd: Path | None = None) -> Path:
    """Return the report path used when the operator does not provide one."""
    if Path("/.dockerenv").exists() or os.getenv("IN_DOCKER"):
        return Path("/reports")
    return (cwd or Path.cwd()) / "reports"
