from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_network_verifier_uses_offline_preflight_and_safe_batch_fixture():
    script = (ROOT / "verify.sh").read_text(encoding="utf-8")

    assert "pocarchitect preflight --offline" in script
    assert "example_usage/dry_run_batch_urls.txt" in script
    assert "--no-ingest" in script
    assert "production-ready" not in script


def test_real_provider_script_checks_openai_and_refuses_placeholder_fixtures():
    script = (ROOT / "test-full.sh").read_text(encoding="utf-8")

    assert "pocarchitect preflight --provider openai" in script
    assert 'REAL_BATCH_FILE="${1:-}"' in script
    assert "Refusing placeholder fixture" in script
    assert 'pocarchitect --batch "$REAL_BATCH_FILE"' in script


def test_batch_template_is_prominently_labeled_and_separate_from_safe_fixture():
    real_template = (ROOT / "example_usage" / "batch_urls.txt").read_text(
        encoding="utf-8"
    )
    dry_run_fixture = (ROOT / "example_usage" / "dry_run_batch_urls.txt").read_text(
        encoding="utf-8"
    )

    assert real_template.startswith("# TEMPLATE ONLY:")
    assert "billable provider" in real_template
    assert "--no-ingest --dry-run" in dry_run_fixture
