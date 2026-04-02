"""
Shared pytest fixtures for POCArchitect-AI-Agent tests.
"""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_llm_response():
    """Return a realistic mock LLM response with all required report sections."""
    return """# PoC Report: CVE-2025-Example Exploit

## Metadata
- **Source URL**: https://github.com/example/poc-repo
- **LLM Provider**: xAI
- **Model**: grok-beta
- **Generation Date**: 2026-04-02

## Summary
This is a buffer overflow vulnerability in the target application allowing remote code execution.

## Build Instructions
1. Clone the repository:
   ```
   git clone https://github.com/example/poc-repo.git
   cd poc-repo

2. Install dependencies
   pip install -r requirements.txt

   Execution Playbook
   # Step 1: Start the vulnerable service
   python vulnerable_server.py

# Step 2: Run the exploit

python exploit.py --target 192.168.1.100 --port 8080

Risk Assessment

Impact: Critical (Remote Code Execution)
Prerequisites: Target running vulnerable version 1.2.3
Detection: Low (no obvious signatures)
Mitigations: Update to version 1.2.4 or later

Weaponized Artifact
# Annotated and weaponized exploit code
import socket
import struct

def main(target, port):
    # Craft malicious payload
    payload = b"A" * 1024 + struct.pack("<I", 0xdeadbeef)
    # ... rest of the exploit
    print(f"[+] Sending exploit to {target}:{port}")

if __name__ == "__main__":
    main("192.168.1.100", 8080)
  ```
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
