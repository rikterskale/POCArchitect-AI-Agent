"""Durable, inspectable state for resumable batch processing."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

STATE_VERSION = 2


class BatchStateError(ValueError):
    """Raised when a state file cannot safely be used."""


def empty_state() -> dict[str, Any]:
    return {"version": STATE_VERSION, "items": {}}


def load_state(path: Path) -> dict[str, Any]:
    """Load a state file without silently discarding corrupt operator history."""
    if not path.exists():
        return empty_state()
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise BatchStateError(
            f"State file is not valid JSON: {path}. Run `batch-reset --batch-state {path} --yes` "
            "to preserve it as a backup and start over."
        ) from error
    if not isinstance(state, dict) or not isinstance(state.get("items"), dict):
        raise BatchStateError(
            f"State file has an unsupported structure: {path}. Use batch-reset to create a backup."
        )
    return state


def write_state(path: Path, state: dict[str, Any]) -> None:
    """Atomically replace a state file so interruption cannot leave partial JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(state, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        prefix=f".{path.name}.",
        suffix=".tmp",
    ) as temporary:
        temporary.write(encoded)
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, path)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise


def summarize_state(state: dict[str, Any]) -> dict[str, int]:
    items = state.get("items", {})
    statuses = [
        item.get("status", "unknown")
        for item in items.values()
        if isinstance(item, dict)
    ]
    return {
        "total": len(items),
        "success": statuses.count("success"),
        "failed": statuses.count("failed"),
        "unknown": len(statuses) - statuses.count("success") - statuses.count("failed"),
    }


def reset_state(path: Path) -> Optional[Path]:
    """Move, rather than delete, the prior state so reset remains recoverable."""
    if not path.exists():
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup = path.with_name(f"{path.stem}.reset-{timestamp}{path.suffix}.bak")
    os.replace(path, backup)
    return backup
