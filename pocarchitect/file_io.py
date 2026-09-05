"""Cross-platform helpers for creating private application files safely."""

from __future__ import annotations

import os
import stat
from pathlib import Path

PRIVATE_FILE_MODE = stat.S_IRUSR | stat.S_IWUSR


def harden_private_descriptor(descriptor: int) -> None:
    """Apply an owner-only POSIX mode when the platform exposes ``fchmod``.

    Windows secures newly created files through inherited ACLs and does not
    provide ``os.fchmod``. The explicit mode passed to ``os.open`` still avoids
    accidentally requesting broader POSIX permissions on supporting systems.
    """
    fchmod = getattr(os, "fchmod", None)
    if fchmod is not None:
        fchmod(descriptor, PRIVATE_FILE_MODE)


def harden_private_path(path: Path) -> None:
    """Reapply owner-only POSIX permissions after an atomic replacement."""
    if os.name != "nt":
        path.chmod(PRIVATE_FILE_MODE)


def open_private_exclusive(path: Path) -> int:
    """Create ``path`` exclusively and return its writable descriptor."""
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        PRIVATE_FILE_MODE,
    )
    try:
        harden_private_descriptor(descriptor)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor
