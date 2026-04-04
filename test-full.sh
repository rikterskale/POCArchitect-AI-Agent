#!/bin/bash
# ================================================
# POCArchitect FULL TEST Script
# Runs real LLM calls (consumes tokens/credits)
# Uses OpenAI by default — change as needed
# ================================================

set -e

echo "=================================================="
echo "🔥 POCArchitect FULL TEST (Real LLM Calls)"
echo " Default provider: OpenAI"
echo "=================================================="
echo "⚠️ This will consume API credits/tokens"
echo "⚠️ Make sure your OPENAI_API_KEY is set in .env"
echo

# 1. Clean install
echo "1. 📦 Installing latest version..."
pip install -e . --force-reinstall
echo "✅ Installed"
echo

# 2. Preflight
echo "2. ✅ Running preflight..."
pocarchitect preflight
echo

# 3. Real Single URL Test (OpenAI)
echo "3. 🔗 Real Single URL Test (OpenAI)..."
pocarchitect --url https://github.com/rikterskale/POCArchitect-AI-Agent \
  --provider openai \
  --model gpt-4o \
  --risk-level High \
  --target-os Linux
echo "✅ Single URL test completed"
echo

# 4. Real Operator Flags Test (OpenAI + verbose)
echo "4. ⚙️ Real Operator Flags Test (OpenAI)..."
pocarchitect --url https://github.com/rikterskale/POCArchitect-AI-Agent \
  --provider openai \
  --model gpt-4o \
  --risk-level Critical \
  --target-os Windows \
  --include-mitigations \
  --verbose
echo "✅ Operator flags test completed"
echo

# 5. Real Batch Mode Test (OpenAI)
echo "5. 📋 Real Batch Mode Test (OpenAI)..."
pocarchitect --batch example_usage/batch_urls.txt \
  --provider openai \
  --model gpt-4o
echo "✅ Batch mode test completed"
echo

# 6. Final status
echo "=================================================="
echo "🎉 FULL TEST COMPLETE!"
echo "=================================================="
echo "📁 Reports saved in: ./reports/"
echo
echo "All tests ran with --provider openai --model gpt-4o"
echo "=================================================="

# Show the latest reports
echo "Latest generated reports:"
ls -1 reports/ 2>/dev/null | tail -n 8 || echo "No reports found"
