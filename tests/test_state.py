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
