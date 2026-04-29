# elko-skills on Cursor

Cursor reads MCP server config from `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project-level).

---

## Auto-configure

```bash
python3 install_mcp.py contacts
python3 install_mcp.py threads
```

Writes to `~/.cursor/mcp.json` automatically.

---

## Manual setup

Edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "elko-contacts": {
      "command": "uvx",
      "args": ["elko-contacts"]
    },
    "elko-threads": {
      "command": "uvx",
      "args": ["elko-threads"]
    }
  }
}
```

Or local path (before PyPI publish):

```json
{
  "mcpServers": {
    "elko-contacts": {
      "command": "python3",
      "args": ["/path/to/elko-skills/contacts/mcp_server.py"]
    }
  }
}
```

---

## Sandbox install

```bash
python3 install_mcp.py contacts --sandbox
# Purge: rm -rf ~/.elko-sandbox
```

---

## Verify

Restart Cursor after editing the config. Tools appear in the MCP tools panel.
