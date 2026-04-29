# elko-threads MCP server
#
# Build context: repo root (needs elko_util.py alongside threads/)
#   docker build -f threads/Dockerfile .
#
# Run (MCP stdio — Hermes / Claude Desktop / Cursor):
#   docker run -i --rm \
#     -v elko-threads-data:/data \
#     ghcr.io/jsoprych/elko-threads:latest

FROM python:3.12-slim

# ── Labels (OCI standard) ──────────────────────────────────
LABEL org.opencontainers.image.title="elko-threads" \
      org.opencontainers.image.description="Cross-channel conversation tracking for AI agents" \
      org.opencontainers.image.source="https://github.com/jsoprych/elko-skills" \
      org.opencontainers.image.licenses="MIT"

# ── Non-root user ──────────────────────────────────────────
RUN useradd -m -u 1000 app

# ── Dependencies (cached layer) ────────────────────────────
RUN pip install --no-cache-dir fastmcp

# ── Application files ──────────────────────────────────────
WORKDIR /app

COPY --chown=app:app elko_util.py .
COPY --chown=app:app threads/__init__.py   threads/
COPY --chown=app:app threads/threads.py    threads/
COPY --chown=app:app threads/schema.sql    threads/
COPY --chown=app:app threads/mcp_server.py threads/
COPY --chown=app:app threads/pyproject.toml threads/

# ── Runtime ────────────────────────────────────────────────
USER app

VOLUME ["/data"]
ENV ELKO_THREADS_DB=/data/threads.db

ENTRYPOINT ["python3", "/app/threads/mcp_server.py"]
