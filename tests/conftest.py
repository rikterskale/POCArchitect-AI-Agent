"""
Shared pytest fixtures for POCArchitect-AI-Agent tests.
"""

import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_llm_response():
    """Return a realistic mock LLM response with all required report sections."""
    return (
        "# PoC Report: CVE-2025-Example Exploit\n"
        "\n"
        "## Metadata\n"
        "- **Source URL**: https://github.com/example/poc-repo\n"
        "- **LLM Provider**: xAI\n"
        "- **Model**: grok-beta\n"
        "- **Generation Date**: 2026-04-02\n"
        "\n"
        "## Summary\n"
        "This is a buffer overflow vulnerability in the target application "
        "allowing remote code execution.\n"
        "\n"
        "## Build Instructions\n"
        "1. Clone the repository:\n"
        "   ```bash
        "   git clone https://github.com/example/poc-repo.git\n"
        "   cd poc-repo\n"
        "   ```\n"
        "\n"
        "2. Install dependencies:\n"
        "   ```bash\n"
        "   pip install -r requirements.txt\n"
        "   ```\n"
        "\n"
        "## Execution Playbook\n"
        "```bash\n"
        "# Step 1: Start the vulnerable service\n"
        "python vulnerable_server.py\n"
        "\n"
        "# Step 2: Run the exploit\n"
        "python exploit.py --target 192.168.1.100 --port 8080\n"
        "```\n"
        "\n"
        "## Risk Assessment\n"
        "- **Impact**: Critical (Remote Code Execution)\n"
        "- **Prerequisites**: Target running vulnerable version 1.2.3\n"
        "- **Detection**: Low (no obvious signatures)\n"
        "- **Mitigations**: Update to version 1.2.4 or later\n"
        "\n"
        "## Weaponized Artifact\n"
        "```python\n"
        "# Annotated and weaponized exploit code\n"
        "import socket\n"
        "import struct\n"
        "\n"
        "def main(target, port):\n"
        "    # Craft malicious payload\n"
        '    payload = b"A" * 1024 + struct.pack("<I", 0xdeadbeef)\n'
        "    # ... rest of the exploit\n"
        '    print(f"[+] Sending exploit to {target}:{port}")\n'
        "\n"
        'if __name__ == "__main__":\n'
        '    main("192.168.1.100", 8080)\n'
        "```\n"
    )


@pytest.fixture
def mock_llm_client(mock_llm_response):
    """Mock LLM client that returns a consistent structured report."""
    client = MagicMock()
    client.generate.return_value = mock_llm_response
    client.provider = "xai"
    client.model = "grok-beta"
    return client


@pytest.fixture
def sample_poc_url():
    """A sample GitHub PoC URL for testing."""
    return "https://github.com/example/poc-repo"


@pytest.fixture
def sample_batch_file(tmp_path):
    """Create a temporary batch file with multiple URLs."""
    batch_file = tmp_path / "pocs.txt"
    batch_file.write_text(
        "https://github.com/example/poc1\n"
        "https://github.com/example/poc2\n"
        "https://raw.githubusercontent.com/example/raw-poc.py\n"
    )
    return batch_file
