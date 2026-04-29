# elko-skills

**Persistent, structured skills for AI agents — available as MCP servers.**

AI agents have no memory between sessions. elko-skills fix that: each skill is a Python module wrapping a SQLite database, exposed as an MCP server so any agent can use it as native tools.

```
elko-skill = MCP server + Python module + SQLite DB
```

---

## Install (any agent, any platform)

```bash
# Contacts
uvx elko-contacts          # or: pip install elko-contacts

# Threads
uvx elko-threads           # or: pip install elko-threads
```

Add to your agent's MCP config:

```json
{
  "mcpServers": {
    "elko-contacts": {
      "command": "uvx",
      "args": ["elko-contacts"],
      "env": { "ELKO_SUPER_ADMIN_EMAIL": "you@example.com" }
    },
    "elko-threads": { "command": "uvx", "args": ["elko-threads"] }
  }
}
```

Or auto-configure all detected platforms in one command:

```bash
git clone https://github.com/jsoprych/elko-skills.git
cd elko-skills
python3 install_mcp.py contacts    # detects Claude Desktop, Claude Code, Cursor, Windsurf, Zed
python3 install_mcp.py threads
python3 install_mcp.py all         # install everything
python3 install_mcp.py contacts --sandbox   # isolated DB, zero footprint, easy purge
python3 install_mcp.py --list-platforms     # see what's detected
```

---

## Platform support

| Platform | Install | Config location |
|---|---|---|
| **Claude Desktop** | `install_mcp.py` or manual | `claude_desktop_config.json` |
| **Claude Code** | `install_mcp.py` or manual | `~/.claude/settings.json` |
| **Cursor** | `install_mcp.py` or manual | `~/.cursor/mcp.json` |
| **Windsurf** | `install_mcp.py` or manual | `~/.codeium/windsurf/mcp_config.json` |
| **Zed** | `install_mcp.py` or manual | `~/.config/zed/settings.json` |
| **VS Code** | snippet (see install_mcp.py) | `.vscode/mcp.json` |
| **Hermes** | `./install.sh contacts` | bootstrap registry |
| **OpenCode** | `./install.sh contacts` | `.opencode/config` |
| **Codex CLI** | `./install.sh contacts` | `.codex/config.yaml` |

See [`docs/platforms/`](docs/platforms/) for full per-platform guides.

---

## Skills

| Skill | PyPI | What | Tools | Tests |
|---|---|---|---|---|
| **elko-contacts** | `pip install elko-contacts` | People, permissions, platforms | 9 | 41 ✓ |
| **elko-threads** | `pip install elko-threads` | Cross-channel conversation tracking | 7 | 29 ✓ |
| **elko_util** | `pip install elko-util` | Core library (shared dependency) | — | — |

### elko-contacts tools

```
list_contacts                              → all contacts
find_contact(query)                        → fuzzy search by name or email
get_contact(email)                         → one contact + phones + platforms
contact_permissions(email)                 → auth rules for a contact
is_super_admin(email)                      → role check
contacts_summary                           → "12 contacts (1 admin, 5 family)"
skill_version                              → "0.1.0" (synced with pyproject.toml + git tag)

add_contact(name, email, requester_email)        → requires super-admin
update_contact(email, requester_email, ...)      → requires super-admin
grant_permission(email, permission, ...)         → requires super-admin
```

### elko-threads tools

```
active_threads(limit)        → active threads, newest first
list_threads(status)         → all threads, filterable
thread_context(topic)        → full message history for a thread
recent_threads(limit)        → latest activity across all threads
threads_summary              → "8 threads (5 active), 34 messages"
skill_version                → "0.1.0" (synced with pyproject.toml + git tag)

capture_message(topic, channel, from_addr, ...)  → add a message; creates thread if new
tag_thread(topic, tag)                           → tag a thread
```

---

## Direct Python access (Hermes / advanced)

Skills are also plain Python modules — import directly if your agent runs Python:

```python
from contacts import contacts

contacts.list_all()
contacts.find('john')
contacts.add('Pat Smith', 'pat@example.com', requester_email='john@elko.ai')
contacts.update('pat@example.com', 'john@elko.ai', circle='work')
contacts.grant('pat@example.com', 'email.send', requester_email='john@elko.ai')
```

```python
from threads import threads

threads.active()
threads.capture('AI-World-Daily', 'email', msg, participants=['john@elko.ai'])
threads.context('AI-World-Daily')
threads.tag('AI-World-Daily', 'important')
threads.summary()
```

---

## Security

**Two-layer SQL injection defense — every skill, every write:**

1. All values use `?` parameterized placeholders — never string-interpolated
2. All column names validated against a whitelist — `safe_update()` rejects unknown columns

```python
# Stored literally, never executed:
dangerous = "Robert'); DROP TABLE contacts; --"
contacts.update('alice@example.com', 'admin@elko.ai', name=dangerous)
# → table still exists; name stored verbatim
```

Every write function checks `requester_email` before touching data. Reads need no auth.

---

## Cross-skill references

Skills are independent — each has its own SQLite DB. They can coexist or run standalone.
Cross-skill references use **email as the universal natural key**, never integer IDs:

```
elko-threads.participants  →  ["john@elko.ai", "pat@example.com"]  (not contact IDs)
elko-audit.actor_email     →  "john@elko.ai"
elko-tasks.assignee_email  →  "pat@example.com"
```

No cross-DB foreign key enforcement — skills compose without hard dependencies.

---

## The pattern: functions are the API

Every elko-skill follows the same structure:

```python
from elko_util import ElkoSkill, safe_update

_skill = ElkoSkill(name='contacts', env_var='ELKO_CONTACTS_DB', ...)

def list_all():
    return _skill.query_all("SELECT ...")

def update(email, requester_email, **kwargs):
    if not is_super_admin(conn, requester_email):
        return {"error": "Permission denied."}
    sql, params = safe_update('contacts', kwargs, 'email = ?', [email], ALLOWED_COLUMNS)
    conn.execute(sql, params)
```

| Convention | Why |
|---|---|
| Every function returns dicts | Consistent, JSON-serializable |
| Writes check permissions first | Every mutation is guarded |
| `safe_update` validates column whitelist | SQL injection defense line 2 |
| `?` placeholders for all values | SQL injection defense line 1 |
| DB path via `ELKO_{NAME}_DB` env var | Separate test/prod/sandbox DBs |

---

## Sandbox mode

Zero-footprint evaluation — all DBs in `~/.elko-sandbox/`, real data untouched:

```bash
python3 install_mcp.py contacts --sandbox
python3 install_mcp.py threads --sandbox
# To purge everything: rm -rf ~/.elko-sandbox
```

---

## Creating a new elko-skill

```bash
cp -r template/ my-skill/
# Edit: schema.sql, module.py, init.py, mcp_server.py
# Test:    python3 -m pytest my-skill/tests/
# Package: edit my-skill/pyproject.toml
# Ship:    python3 -m build && twine upload dist/*
```

See [`template/`](template/) and [`docs/howto-create-a-skill.md`](docs/howto-create-a-skill.md).

---

## Roadmap

### Built ✅
- [x] **elko-contacts** — people, permissions, platforms (41 tests)
- [x] **elko-threads** — cross-channel conversation tracking (29 tests)
- [x] **elko_util** — core library, safe SQL builders, ElkoSkill base class
- [x] **MCP servers** — `contacts/mcp_server.py`, `threads/mcp_server.py` (fastmcp)
- [x] **PyPI packages** — `elko-contacts`, `elko-threads`, `elko-util`
- [x] **install_mcp.py** — auto-configures Claude Desktop, Claude Code, Cursor, Windsurf, Zed
- [x] **Sandbox mode** — isolated DBs, one-line purge
- [x] **Template** — starter kit for new elko-skills
- [x] **Platform guides** — Hermes, Claude Code, Codex CLI, OpenCode, Cursor, Windsurf, Zed

### Next 🔨
- [ ] **elko-credentials** — API keys, tokens, secrets (encrypted at rest)
- [ ] **elko-audit** — timestamped action log across all skills
- [ ] **elko-tasks** — persistent todos/tasks for agents
- [ ] **elko-notes** — unstructured knowledge base
- [ ] Smithery + PulseMCP marketplace listings
- [ ] Read the Docs site

### Future 🚀
- [ ] **elko-iam** — central permissions service (extract from per-skill)
- [ ] **elko-projects** — long-running work tracking
- [ ] HTTP transport mode for container deployments
- [ ] elko-foundry architecture

---

## Directory structure

```
elko-skills/
├── install_mcp.py          ← Auto-configure MCP for all detected platforms
├── install.sh              ← Classic installer (Hermes, OpenCode, Codex)
├── elko_util.py            ← Core library: ElkoSkill, safe_update, is_super_admin
├── pyproject.toml          ← elko-util PyPI package
├── README.md               ← You are here
├── contacts/
│   ├── contacts.py         ← Module (the API)
│   ├── mcp_server.py       ← MCP server (uvx elko-contacts)
│   ├── pyproject.toml      ← PyPI: elko-contacts
│   ├── smithery.yaml       ← Smithery marketplace manifest
│   ├── README.md           ← PyPI description
│   ├── __init__.py
│   ├── init_contacts.py    ← First-run DB creation
│   ├── schema.sql
│   ├── docs/howto.md
│   └── tests/
├── threads/
│   ├── threads.py
│   ├── mcp_server.py       ← MCP server (uvx elko-threads)
│   ├── pyproject.toml      ← PyPI: elko-threads
│   ├── smithery.yaml       ← Smithery marketplace manifest
│   ├── README.md           ← PyPI description
│   ├── __init__.py
│   ├── init_threads.py
│   ├── schema.sql
│   ├── docs/howto.md
│   └── tests/
├── template/               ← Starter kit for new elko-skills
└── docs/
    ├── howto-create-a-skill.md
    └── platforms/
        ├── claude-code.md
        ├── cursor.md
        ├── windsurf.md
        ├── hermes.md
        ├── opencode.md
        └── codex.md
```

---

## License

MIT — elko.ai
