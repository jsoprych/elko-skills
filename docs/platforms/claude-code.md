# elko-skills on Claude Code

Claude Code supports MCP servers natively. The recommended setup is MCP — skills appear as first-class tools in every session.

---

## MCP setup (recommended)

### Option A — Auto-configure

```bash
python3 install_mcp.py contacts
python3 install_mcp.py threads
```

Detects Claude Code and writes to `~/.claude/settings.json` automatically.

### Option B — One-liner via Claude Code CLI

```bash
claude mcp add elko-contacts uvx elko-contacts
claude mcp add elko-threads  uvx elko-threads
```

### Option C — Manual

Edit `~/.claude/settings.json`:

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

Or with a local clone (before PyPI publish):

```json
{
  "mcpServers": {
    "elko-contacts": {
      "command": "python3",
      "args": ["~/.elko-skills/contacts/mcp_server.py"]
    }
  }
}
```

---

## Sandbox install (safe evaluation)

```bash
python3 install_mcp.py contacts --sandbox
python3 install_mcp.py threads  --sandbox
```

All DBs go to `~/.elko-sandbox/`. Purge everything: `rm -rf ~/.elko-sandbox`.

---

## Verify

```bash
claude mcp list                  # should show elko-contacts, elko-threads
claude mcp get elko-contacts     # shows tools list
```

Or test the server directly:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | python3 ~/.elko-skills/contacts/mcp_server.py 2>/dev/null
```

---

## Tools available in Claude Code

Once configured, agents see these as native tools:

**elko-contacts:** `list_all`, `find`, `get`, `get_permissions`, `check_is_super_admin`, `summary`, `add`, `update`, `grant`

**elko-threads:** `active`, `all_threads`, `context`, `recent`, `summary`, `capture`, `tag`

---

## CLAUDE.md snippet (optional context)

Add to your project's `CLAUDE.md` so Claude knows the skills are available:

```markdown
## Persistent skills available

- **elko-contacts** MCP: contact list with permissions. Use `list_all`, `find`, `get`, `add`.
- **elko-threads** MCP: conversation tracking. Use `active`, `capture`, `context`.

Writes require `requester_email` of a super-admin contact.
```

---

## Env var configuration

Override DB locations (useful for project-specific data):

```bash
export ELKO_CONTACTS_DB=/path/to/contacts.db
export ELKO_THREADS_DB=/path/to/threads.db
```

Or set in the MCP config:

```json
{
  "mcpServers": {
    "elko-contacts": {
      "command": "uvx",
      "args": ["elko-contacts"],
      "env": {
        "ELKO_CONTACTS_DB": "/path/to/contacts.db"
      }
    }
  }
}
```
