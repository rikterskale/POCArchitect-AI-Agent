POCArchitect Usage Guide
This document outlines all available command-line options for POCArchitect.

POCArchitect Agent Usage Guide
Command Line Options
Option	Description	Default
--url /-u	Single URL or path to .txt batch file	Required
--provider / -p	xai, openai, groq, local	xai
--api-key / -k	Override API key	From .env
--model` / -m	Model name	Auto-selected
--risk-level	Critical, High, Medium, Low, auto	auto
--target-os`	Windows, Linux, macOS, cross-platform, auto	auto
--include-mitigations / --no-mitigations	Include mitigation section	true
--no-ingest`	Skip GitHub grounding	false
--output-dir / -o	Output directory	./reports
--verbose / -v	Verbose output	false
--dry-run	Show full prompt without calling LLM	false
Batch Mode
Pass a text file to --url: pocarchitect --url example_usage/batch_urls.txt --provider xai

The tool will:

Process every URL in the file
Generate one report per URL
Create index.md with links to all reports
Examples
Single PoC with custom settings
pocarchitect --url https://github.com/...
--risk-level Critical
--target-os Windows
--no-mitigations

Batch processing
pocarchitect --url batch_urls.txt

Dry-Run Mode
Use --dry-run to inspect the exact prompt that will be sent to the LLM without making any API call. This is very useful for:

Debugging prompt quality
Tuning operator flags
Verifying zero-hallucination behavior
Full Options
pocarchitect --help
Tips
Set temperature to 0.0 for maximum consistency.
Use --verbose when troubleshooting.
Last Updated: April 02, 2026

For more details, see:

ARCHITECTURE.md
DOCKER.md
