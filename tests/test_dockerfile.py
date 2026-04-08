from pathlib import Path


def test_dockerfile_reports_directory_owned_by_runtime_user():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "RUN useradd -m -s /bin/bash pocuser" in dockerfile
    assert "chown -R pocuser:pocuser /reports" in dockerfile
    assert "USER pocuser" in dockerfile


def test_dockerfile_sets_owner_before_switching_user():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    useradd_index = dockerfile.index("RUN useradd -m -s /bin/bash pocuser")
    chown_index = dockerfile.index("chown -R pocuser:pocuser /reports")
    user_switch_index = dockerfile.index("USER pocuser")

    assert useradd_index < chown_index < user_switch_index
