# =============================================================================
# POCArchitect-AI-Agent Docker Image
# =============================================================================

FROM python:3.11-slim

# Set labels
LABEL maintainer="rikterskale"
LABEL description="POCArchitect - AI-powered PoC to Markdown blueprint generator"
LABEL version="0.1.0"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POCARCHITECT_OUTPUT_DIR=/app/reports

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash pocuser

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (better layer caching)
COPY pyproject.toml requirements.txt* ./

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    else \
        pip install -e .; \
    fi

# Copy the rest of the application
COPY . .

# Create reports directory and set permissions
RUN mkdir -p /app/reports && \
    chown -R pocuser:pocuser /app

# Switch to non-root user
USER pocuser

# Set volume for reports output
VOLUME ["/app/reports"]

# Default command
ENTRYPOINT ["pocarchitect"]

# Show help by default
CMD ["--help"]
