# POCArchitect AI Agent - Dockerfile (v0.2.2) - Reliable saving on Windows
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY pocarchitect/ ./pocarchitect/

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .[all]

# Final stage
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Create reports directory with open permissions
RUN mkdir -p /reports && chmod -R 777 /reports

RUN useradd -m -s /bin/bash pocuser

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

USER pocuser

VOLUME ["/reports"]

ENTRYPOINT ["pocarchitect"]
CMD ["--help"]