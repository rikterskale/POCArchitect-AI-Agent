POCArchitect AI Agent
Turn any Proof-of-Concept URL into a clean, reproducible, weaponized Markdown blueprint — built for red teamers and offensive security operators.

Features
GitHub PoC grounding (shallow clone + smart file extraction)
Fully functional batch mode (--url batch_urls.txt)
Operator controls:
--risk-level
--target-os
--include-mitigations
--no-mitigations
Automatic preflight checks on every run
Multi-provider support (xAI/Grok, OpenAI, Groq, local Ollama)
Smart Docker volume support (reports saved to /reports by default inside containers)
Retry logic + timeouts on LLM calls
Quick Start
# 1. Clone & install
git clone https://github.com/rikterskale/POCArchitect-AI-Agent.git
cd POCArchitect-AI-Agent
cp .env.example .env          # ← Add your XAI_API_KEY (or OPENAI_API_KEY)
pip install -e .

# 2. Run preflight (optional — now runs automatically)
pocarchitect preflight

# 3. Single URL
pocarchitect --url https://github.com/rikterskale/POCArchitect-AI-Agent --provider xai

# 4. Batch mode (exactly as documented)
pocarchitect --url example_usage/batch_urls.txt --provider xai
Usage
pocarchitect --url <URL or batch file> [OPTIONS]
Options
--provider xai|openai|groq|local
--risk-level Critical|High|Medium|Low|auto
--target-os Windows|Linux|macOS|cross-platform|auto
--include-mitigations / --no-mitigations
--no-ingest — Skip grounding for very large repos
--output-dir ./reports
--verbose
Reports are saved to ./reports/ (or /reports inside Docker).

Docker
docker build -t pocarchitect .
docker run -v "$(pwd)/reports:/reports" \
  -e XAI_API_KEY=your_key_here \
  pocarchitect --url https://github.com/... --provider xai

No --output-dir flag needed anymore — it automatically uses the mounted volume.

