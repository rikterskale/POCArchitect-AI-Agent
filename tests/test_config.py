from pathlib import Path

from pocarchitect.config import DEFAULT_MODELS, default_output_dir


def test_default_output_directory_honors_in_docker(tmp_path, monkeypatch):
    monkeypatch.setenv("IN_DOCKER", "1")

    assert default_output_dir(tmp_path) == Path("/reports")


def test_every_cli_provider_has_a_default_model():
    assert set(DEFAULT_MODELS) == {"xai", "openai", "groq", "local"}
