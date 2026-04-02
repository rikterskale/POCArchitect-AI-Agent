# Dry run - see the prompt without spending tokens
pocarchitect --url https://github.com/example/poc --dry-run

# Verbose + specific options
pocarchitect --url https://github.com/example/poc \
  --risk-level Critical \
  --target-os Windows \
  --verbose
