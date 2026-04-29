# elko-contacts

**Persistent contact list with permissions for AI agents.**

AI agents lose their contacts between sessions. `elko-contacts` gives agents a real, persistent people database — accessible as MCP tools so any agent can use it natively.

## Install

```bash
pip install elko-contacts
# or: uvx elko-contacts  (zero-install, via uv)
```

## MCP setup (any agent)

```json
{
  "mcpServers": {
    "elko-contacts": {
      "command": "uvx",
      "args": ["elko-contacts"]
    }
  }
}
```

Add to `claude_desktop_config.json`, `~/.cursor/mcp.json`, `~/.codeium/windsurf/mcp_config.json`, or any MCP-compatible config.

Or auto-configure all detected platforms:

```bash
python3 install_mcp.py contacts
python3 install_mcp.py contacts --sandbox   # isolated DB, easy purge
```

## Tools

| Tool | Auth | Description |
|------|------|-------------|
| `list_all` | — | All contacts |
| `find(query)` | — | Fuzzy search by name or email |
| `get(email)` | — | One contact with phones and platform handles |
| `get_permissions(email)` | — | Auth rules for a contact |
| `check_is_super_admin(email)` | — | Role check |
| `summary` | — | `"12 contacts (1 admin, 5 family)"` |
| `add(name, email, requester_email)` | super-admin | Add a contact |
| `update(email, requester_email, ...)` | super-admin | Update fields |
| `grant(email, permission, requester_email)` | super-admin | Grant a permission |

## Python API (direct access)

```python
from contacts import contacts

# Reads — no auth needed
contacts.list_all()
contacts.find('john')
contacts.get_by_email('john@elko.ai')
contacts.check_is_super_admin('john@elko.ai')
contacts.get_permissions('diana@example.com')

# Writes — every one checks requester_email
contacts.add('Pat Smith', 'pat@example.com', requester_email='john@elko.ai')
contacts.update('pat@example.com', 'john@elko.ai', circle='work')
contacts.grant('pat@example.com', 'email.send', requester_email='john@elko.ai')
```

## Security

- All values use `?` parameterized placeholders
- Column names validated against a whitelist (`safe_update`)
- Every write checks `requester_email` against the permissions table
- 41 tests including 5 dedicated SQL injection resistance tests

## Configuration

```bash
export ELKO_CONTACTS_DB=/path/to/contacts.db   # override DB location
```

Default DB location: `contacts/contacts.db` (relative to module).

## Schema

- `contacts` — id, name, email, role, circle, discretion, metadata (JSON)
- `contact_phones` — id, contact_id, label, number
- `contact_platforms` — id, contact_id, platform, platform_id, label
- `auth_rules` — id, contact_id, permission, scope

## Links

- [Full docs](https://github.com/jsoprych/elko-skills/tree/main/contacts/docs)
- [Platform setup guides](https://github.com/jsoprych/elko-skills/tree/main/docs/platforms)
- [elko-skills repo](https://github.com/jsoprych/elko-skills)

## License

MIT — elko.ai
