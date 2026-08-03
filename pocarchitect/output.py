"""Stable, presentation-independent CLI output helpers."""

from __future__ import annotations

from typing import Any


def event_payload(event: str, message: str, **details: Any) -> dict[str, Any]:
    """Return the documented JSON-lines event shape used by ``--format json``."""
    return {"event": event, "message": message, **details}
