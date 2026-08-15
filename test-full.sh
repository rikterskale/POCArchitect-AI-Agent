#!/bin/bash
# ================================================
# POCArchitect FULL TEST Script
# Runs real LLM calls (consumes tokens/credits)
# Uses OpenAI by default — change as required
# ================================================

set -e

REAL_BATCH_FILE="${1:-}"
if [ -z "$REAL_BATCH_FILE" ]; then
  echo "Usage: ./test-full.sh <authorized-real-batch-file>"
  echo "The repository example files are placeholders and are refused for billable runs."
  exit 2
fi

case "$REAL_BATCH_FILE" in
  example_usage/batch_urls.txt|example_usage/dry_run_batch_urls.txt)
    echo "Refusing placeholder fixture for a billable provider run: $REAL_BATCH_FILE"
    exit 2
    ;;
esac

if [ ! -f "$REAL_BATCH_FILE" ]; then
  echo "Authorized batch file not found: $REAL_BATCH_FILE"
  exit 2
fi

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
pocarchitect preflight --provider openai
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
pocarchitect --batch "$REAL_BATCH_FILE" \
  --provider openai \
  --model gpt-4o
echo "✅ Batch mode test completed with zero failed items"
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
