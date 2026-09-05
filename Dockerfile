# POCArchitect AI Agent - Dockerfile (v0.2.0) - Reliable saving on Windows
FROM python:3.14.7-slim-bookworm AS builder

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY pocarchitect/ ./pocarchitect/

RUN python -m venv "$VIRTUAL_ENV" \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Final stage
FROM python:3.14.7-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash pocuser

# Create reports directory and grant runtime user write access
RUN mkdir -p /reports && chown -R pocuser:pocuser /reports && chmod -R 775 /reports

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

USER pocuser

VOLUME ["/reports"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 CMD ["pocarchitect", "doctor", "--offline"]

ENTRYPOINT ["pocarchitect"]
CMD ["--help"]
