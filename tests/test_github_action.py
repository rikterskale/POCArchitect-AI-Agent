from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / "action.yml"
SCHEDULED = ROOT / ".github" / "workflows" / "pocarchitect-scheduled.yml"


def test_github_action_composite_installs_runs_comments_and_uploads():
    text = ACTION.read_text(encoding="utf-8")

    assert "using: composite" in text
    assert "required: true" in text
    assert 'default: "true"' in text
    assert "python -m pip install" in text
    assert "--source" in text
    assert "--yes" in text
    assert "--format json" in text
    assert "--dry-run" in text
    assert "POCA_PROVIDER" in text
    assert "gh pr comment" in text
    assert "POCAnalysis_*.md" in text
    assert "actions/upload-artifact@v4" in text
    assert "if-no-files-found: error" in text
    assert "path: reports/" in text
    assert "inputs.dry-run != 'true'" in text
    assert "github.event_name == 'pull_request'" in text


def test_scheduled_workflow_invokes_the_composite_action_in_dry_run():
    text = SCHEDULED.read_text(encoding="utf-8")

    assert "uses: ./" in text
    assert 'dry-run: "true"' in text
    assert "source:" in text
