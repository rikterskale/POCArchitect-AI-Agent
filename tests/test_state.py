import json

import pytest

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
