"""
Tests for the preflight checker in POCArchitect-AI-Agent.
Validates environment readiness, Python version, and API key checks.
"""

import pytest
import sys
from unittest.mock import patch, MagicMock

# Adjust the import based on where your preflight_checker is located.
# Common options:
# from preflight_checker import run_preflight_check
# OR
# from pocarchitect.preflight import run_preflight_check

# TODO: Update the import below to match your actual file/structure
try:
    from preflight_checker import run_preflight_check
except ImportError:
    # Fallback if you move it into the package later
    from pocarchitect.preflight import run_preflight_check


class TestPreflightChecker:

    def test_python_version_supported(self):
        """Test that current Python version (or mocked supported version) passes."""
        with patch('sys.version_info', (3, 11, 5)):
            # Assuming your checker returns True/None on success or doesn't raise
            result = run_preflight_check()
            assert result is True or result is None, "Supported Python version should pass"

    def test_python_version_too_old(self):
        """Test that very old Python versions are rejected."""
        with patch('sys.version_info', (3, 7, 0)):
            with pytest.raises((SystemExit, RuntimeError, Exception)):
                run_preflight_check()

    @patch('preflight_checker.check_api_keys')   # Change this if your function name is different
    def test_missing_api_key_raises_error(self, mock_check_api_keys):
        """Test that missing API keys cause the preflight to fail."""
        mock_check_api_keys.return_value = False

        with pytest.raises((SystemExit, RuntimeError, Exception)):
            run_preflight_check()

    @patch('preflight_checker.check_api_keys')
    def test_all_api_keys_present_passes(self, mock_check_api_keys):
        """Test that having valid API keys allows preflight to succeed."""
        mock_check_api_keys.return_value = True

        result = run_preflight_check()
        assert result is True or result is None

    def test_preflight_with_no_arguments(self):
        """Test calling preflight without arguments (should still run)."""
        with patch('sys.version_info', (3, 11, 0)):
            with patch('preflight_checker.check_api_keys', return_value=True):
                result = run_preflight_check()
                assert result is True or result is None


# Optional: Add more specific tests once you show me the actual preflight_checker.py code
