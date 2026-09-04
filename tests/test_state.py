import json

import pytest

from pocarchitect import state
from pocarchitect.state import BatchStateError, load_state


def test_state_loader_rejects_unsupported_versions_without_overwriting(tmp_path):
    path = tmp_path / "batch_progress.json"
    original = {"version": 1, "items": {"https://example.com": {"status": "success"}}}
    path.write_text(json.dumps(original), encoding="utf-8")

    with pytest.raises(BatchStateError, match="version 2"):
        load_state(path)

    assert json.loads(path.read_text(encoding="utf-8")) == original


def test_state_loader_rejects_invalid_item_shapes(tmp_path):
    path = tmp_path / "batch_progress.json"
    path.write_text(json.dumps({"version": 2, "items": {"x": "bad"}}), encoding="utf-8")
    with pytest.raises(BatchStateError, match="invalid item"):
        load_state(path)


def test_state_loader_rejects_unknown_status(tmp_path):
    path = tmp_path / "batch_progress.json"
    path.write_text(
        json.dumps({"version": 2, "items": {"x": {"status": "new"}}}), encoding="utf-8"
    )
    with pytest.raises(BatchStateError, match="invalid status"):
        load_state(path)


def test_state_writer_releases_lock_when_serialization_fails(tmp_path):
    path = tmp_path / "batch_progress.json"

    with pytest.raises(TypeError):
        state.write_state(path, {"version": 2, "items": {}, "bad": object()})

    assert not (tmp_path / ".batch_progress.json.lock").exists()
    assert list(tmp_path.glob(".batch_progress.json.*.tmp")) == []


def test_state_summary_and_recoverable_reset(tmp_path):
    value = {
        "version": 2,
        "items": {
            "ok": {"status": "success"},
            "bad": {"status": "failed"},
        },
    }
    path = tmp_path / "batch_progress.json"
    state.write_state(path, value)

    assert state.summarize_state(value) == {
        "total": 2,
        "success": 1,
        "failed": 1,
        "unknown": 0,
    }
    backup = state.reset_state(path)
    assert backup is not None and backup.read_text(encoding="utf-8")
    assert not path.exists()


def test_state_writer_cleans_lock_and_temporary_file_when_replace_fails(
    tmp_path, monkeypatch
):
    path = tmp_path / "state.json"
    monkeypatch.setattr(
        state.os,
        "replace",
        lambda source, destination: (_ for _ in ()).throw(OSError("replace failed")),
    )

    with pytest.raises(OSError, match="replace failed"):
        state.write_state(path, state.empty_state())

    assert not (tmp_path / ".state.json.lock").exists()
    assert list(tmp_path.glob(".state.json.*.tmp")) == []


def test_state_writer_times_out_on_existing_lock(tmp_path, monkeypatch):
    path = tmp_path / "state.json"
    (tmp_path / ".state.json.lock").touch()
    moments = iter((0.0, state.LOCK_TIMEOUT_SECONDS + 1.0))
    monkeypatch.setattr(state.time, "monotonic", lambda: next(moments))
    monkeypatch.setattr(state.time, "sleep", lambda _: None)

    with pytest.raises(state.BatchStateError, match="Timed out waiting"):
        state.write_state(path, state.empty_state())


def test_state_writer_waits_for_lock_and_reset_missing_is_noop(tmp_path, monkeypatch):
    path = tmp_path / "batch.json"
    attempts = 0
    original_open = state.os.open

    def delayed_open(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise FileExistsError
        return original_open(*args, **kwargs)

    monkeypatch.setattr(state.os, "open", delayed_open)
    monkeypatch.setattr(state.time, "sleep", lambda seconds: None)

    state.write_state(path, state.empty_state())

    assert attempts >= 2
    assert state.reset_state(tmp_path / "missing.json") is None
