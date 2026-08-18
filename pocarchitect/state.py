"""Durable, inspectable state for resumable batch processing."""

from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_VERSION = 2
LOCK_TIMEOUT_SECONDS = 10


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
    if (
        not isinstance(state, dict)
        or state.get("version") != STATE_VERSION
        or not isinstance(state.get("items"), dict)
    ):
        raise BatchStateError(
            f"State file must use version {STATE_VERSION} with an object-valued `items` field: "
            f"{path}. Use batch-reset to create a backup."
        )
    for url, item in state["items"].items():
        if not isinstance(url, str) or not url.strip() or not isinstance(item, dict):
            raise BatchStateError(
                f"State file contains an invalid item for {url!r}: {path}"
            )
        if item.get("status") not in {"success", "failed"}:
            raise BatchStateError(
                f"State file contains an invalid status for {url!r}: {path}"
            )
    return state


def write_state(path: Path, state: dict[str, Any]) -> None:
    """Atomically replace a state file so interruption cannot leave partial JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.lock")
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
    lock_fd: int | None = None
    while lock_fd is None:
        try:
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise BatchStateError(f"Timed out waiting for state lock: {path}")
            time.sleep(0.05)
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
    finally:
        os.close(lock_fd)
        lock_path.unlink(missing_ok=True)


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


def reset_state(path: Path) -> Path | None:
    """Move, rather than delete, the prior state so reset remains recoverable."""
    if not path.exists():
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    backup = path.with_name(f"{path.stem}.reset-{timestamp}{path.suffix}.bak")
    os.replace(path, backup)
    return backup
