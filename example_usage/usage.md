# Safe dry run - inspect the prompt without cloning a repository, contacting a provider, or spending tokens.
python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --no-color

# Show the provider-facing prompt with custom labels. This is still a safe dry run.
python -m pocarchitect --url https://github.com/example/poc \
  --no-ingest \
  --dry-run \
  --risk-level Critical \
  --target-os Windows \
  --verbose \
  --no-color
