import os
import stat

from pocarchitect import file_io


def test_private_file_creation_works_without_fchmod(tmp_path, monkeypatch):
    path = tmp_path / "private.txt"
    monkeypatch.delattr(file_io.os, "fchmod", raising=False)

    descriptor = file_io.open_private_exclusive(path)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write("private")
    file_io.harden_private_path(path)

    assert path.read_text(encoding="utf-8") == "private"


def test_private_file_creation_uses_owner_only_posix_mode(tmp_path):
    path = tmp_path / "private.txt"

    descriptor = file_io.open_private_exclusive(path)
    os.close(descriptor)
    file_io.harden_private_path(path)

    if os.name != "nt":
        assert stat.S_IMODE(path.stat().st_mode) == file_io.PRIVATE_FILE_MODE
