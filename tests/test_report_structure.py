"""
Tests for report structure and consistency in POCArchitect-AI-Agent.
Ensures the output always contains required sections regardless of LLM provider.
"""

import pytest
from unittest.mock import patch


@pytest.mark.parametrize("provider,model", [
    ("xai", "grok-beta"),
    ("openai", "gpt-4o"),
    ("anthropic", "claude-3-5-sonnet"),
])
def test_generated_report_contains_required_sections(
    mock_llm_client, sample_poc_url, provider, model
):
    """
    Core test: Verify that the final report always includes all critical sections.
    This enforces consistency across different LLM providers.
    """
    # Mock the LLM client so we don't make real API calls
    with patch('pocarchitect.llm.get_client', return_value=mock_llm_client):
        # TODO: Replace with your actual report generation function name
        report = generate_report(
            url=sample_poc_url,
            provider=provider,
            model=model
        )

    # Critical assertions - these sections must exist in every report
    assert report is not None
    assert len(report.strip()) > 100, "Report should not be empty"

    # Required sections (case-insensitive check)
    report_lower = report.lower()
    required_sections = [
        "metadata",
        "summary",
        "build instructions",
        "execution playbook",
        "risk assessment",
        "weaponized artifact"
    ]

    for section in required_sections:
        assert section in report_lower, f"Missing required section: {section}"

    # Check for markdown code blocks
    assert "```" in report, "Report should contain code blocks"

    # Verify the mock was actually called
    mock_llm_client.generate.assert_called_once()


def test_report_with_batch_file(sample_batch_file, mock_llm_client):
    """Basic test for batch mode (can be expanded later)."""
    # This is a stub - expand when you implement batch processing
    with patch('pocarchitect.llm.get_client', return_value=mock_llm_client):
        # TODO: Replace with your actual batch function if different
        reports = process_batch(sample_batch_file)

    assert isinstance(reports, (list, dict))
    assert len(reports) > 0


# ==================== PLACEHOLDERS ====================
# Replace these with your actual function names once you have them

def generate_report(url: str, provider: str, model: str):
    """Placeholder - replace with actual import from your package."""
    # Example of real import you will use later:
    # from pocarchitect.core.generator import generate_report
    raise NotImplementedError(
        "Replace this placeholder with real call to your report generator.\n"
        "Example: from pocarchitect.core import generate_report"
    )


def process_batch(batch_file):
    """Placeholder for batch processing function."""
    raise NotImplementedError(
        "Replace with your actual batch processing function."
    )
