# elko-contacts MCP server
#
# Build context: repo root (needs elko_util.py alongside contacts/)
#   docker build -f contacts/Dockerfile .
#
# Run (MCP stdio — Hermes / Claude Desktop / Cursor):
#   docker run -i --rm \
#     -e ELKO_SUPER_ADMIN_EMAIL=you@example.com \
#     -v elko-contacts-data:/data \
#     ghcr.io/jsoprych/elko-contacts:latest

FROM python:3.12-slim

# ── Labels (OCI standard) ──────────────────────────────────
LABEL org.opencontainers.image.title="elko-contacts" \
      org.opencontainers.image.description="Persistent contact list with permissions for AI agents" \
      org.opencontainers.image.source="https://github.com/jsoprych/elko-skills" \
      org.opencontainers.image.licenses="MIT"

# ── Non-root user ──────────────────────────────────────────
RUN useradd -m -u 1000 app

# ── Dependencies (cached layer) ────────────────────────────
RUN pip install --no-cache-dir fastmcp

# ── Application files ──────────────────────────────────────
WORKDIR /app

COPY --chown=app:app elko_util.py .
COPY --chown=app:app contacts/__init__.py   contacts/
COPY --chown=app:app contacts/contacts.py   contacts/
COPY --chown=app:app contacts/schema.sql    contacts/
COPY --chown=app:app contacts/mcp_server.py contacts/
COPY --chown=app:app contacts/pyproject.toml contacts/

# ── Runtime ────────────────────────────────────────────────
USER app

VOLUME ["/data"]

# All elko-skill DBs resolve to /data/{name}.db by default in Docker.
# Override individual skills with ELKO_CONTACTS_DB if needed.
ENV ELKO_DATA_DIR=/data

ENTRYPOINT ["python3", "/app/contacts/mcp_server.py"]
