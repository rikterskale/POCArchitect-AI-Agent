# ──────────────────────────────────────────────────────────────
# POCArchitect AI Agent - Production Dockerfile (v0.2.0)
# Multi-stage build for minimal, secure image
# ──────────────────────────────────────────────────────────────

FROM python:3.12-slim AS builder

# Install system dependencies (git is required for grounding context)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only packaging files first (leverage Docker layer cache)
COPY pyproject.toml requirements.txt ./

# Install runtime dependencies + the package itself
# [all] includes anthropic + google-generativeai so every provider works
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e .[all]

# Final runtime stage
FROM python:3.12-slim

# Labels (security scanners / Kubernetes / GitHub Container Registry love these)
LABEL org.opencontainers.image.title="POCArchitect AI Agent"
LABEL org.opencontainers.image.description="Turn raw PoC URLs into weaponized Markdown blueprints"
LABEL org.opencontainers.image.version="0.2.0"
LABEL org.opencontainers.image.authors="RikterSkale"
LABEL org.opencontainers.image.source="https://github.com/rikterskale/POCArchitect-AI-Agent"
LABEL org.opencontainers.image.licenses="MIT"

# Install only the runtime system dependency (git)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN useradd -m -s /bin/bash pocuser && \
    mkdir -p /reports && \
    chown -R pocuser:pocuser /reports

WORKDIR /app

# Copy only the installed Python packages and binaries from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Switch to non-root user
USER pocuser

# Persistent volume for generated reports
VOLUME ["/reports"]

# Default to the CLI (you can still run any subcommand/flag)
ENTRYPOINT ["pocarchitect"]
CMD ["--help"]
