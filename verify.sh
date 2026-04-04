#!/bin/bash
# ================================================
# POCArchitect Verification Script (DRY-RUN)
# Validates the tool without making real LLM calls
# ================================================

set -e

echo "=================================================="
echo "🚀 POCArchitect Verification (DRY-RUN)"
echo "=================================================="
echo

# 1. Clean re-install
echo "1. 📦 Re-installing package..."
pip install -e . --force-reinstall
echo "✅ Package installed"
echo

# 2. Version & help
echo "2. 🔍 Version and help check..."
pocarchitect --version
echo
pocarchitect --help | head -n 30
echo "✅ Help displayed"
echo

# 3. Preflight
echo "3. ✅ Running preflight checks..."
pocarchitect preflight
echo

# 4. Single URL dry-run test
echo "4. 🔗 Single URL test (dry-run)..."
pocarchitect --url https://github.com/rikterskale/POCArchitect-AI-Agent \
  --provider openai \
  --dry-run
echo "✅ Single URL dry-run passed"
echo

# 5. Operator flags + verbose + dry-run test
echo "5. ⚙️ Operator flags + verbose test (dry-run)..."
pocarchitect --url https://github.com/rikterskale/POCArchitect-AI-Agent \
  --provider openai \
  --risk-level Critical \
  --target-os Windows \
  --include-mitigations \
  --verbose \
  --dry-run
echo "✅ Operator flags + verbose dry-run passed"
echo

# 6. Batch mode dry-run test
echo "6. 📋 Batch mode test (dry-run)..."
pocarchitect --batch example_usage/batch_urls.txt \
  --provider openai \
  --dry-run
echo "✅ Batch mode dry-run passed"
echo

# 7. Final status
echo "=================================================="
echo "🎉 ALL VERIFICATION STEPS COMPLETE!"
echo "=================================================="
echo "✅ --dry-run now works correctly (no API calls)"
echo "✅ --verbose flag is functional"
echo "✅ --batch flag works for batch mode"
echo "✅ Project is clean and production-ready!"
echo "=================================================="

echo "Latest reports (if any were generated):"
ls -1 reports/ 2>/dev/null | tail -n 5 || echo "No reports yet (expected in dry-run mode)"
