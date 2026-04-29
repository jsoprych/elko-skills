# elko-skills

**Database-backed, self-initializing structured skills for AI agents.**

An elko-skill is a reusable building block: one Python module wrapping one SQLite database, registered in a global directory, and discoverable at runtime. Every elko-skill is self-contained — create a DB, ship the schema, import the module, call the functions.

```
elko-skill = Python module + SQLite DB + registry entry
```

---

## Why elko-skills?

AI agents (Hermes, Claude Code, Codex, OpenClaw, etc.) have no built-in user database, contact system, or permissions model. They operate per-session with no persistent state. elko-skills fill that gap — they give agents:

- **Persistent state** — survive across restarts, sessions, and agents
- **Structured access** — Python functions wrap raw SQL; the function is the API
- **Permissions** — write operations check authorization before touching data
- **Discoverability** — the registry tells every agent what data is available
- **Marketplace-ready** — ship schema + module + init script; data stays local

---

## Architecture

```
startup.py
  └─► bootstrap.db        ← Identity + reflexes ("check registry first")
         └─► elko-registry.db    ← Pure directory — only services table
                ├─► elko-skills/contacts/    ← schema.sql + contacts.py + contacts.db
                ├─► elko-skills/threads/     ← schema.sql + threads.py + threads.db
                └─► elko-skills/...          ← More to come
```

**Three layers:**

1. **Bootstrap** — Identity, registry pointer, and learned reflexes (rules of thumb). Minimal. Injects on every session start.
2. **Registry** — Pure directory. One table: which services exist, their type, path, and capability. No data lives here.
3. **Elko-skill** — The module. The schema. The functions. The data. Fully stand-alone.

---

## Structure of an elko-skill

Every elko-skill lives in its own directory under `elko-skills/`:

```
elko-skills/
├── contacts/
│   ├── schema.sql         ← CREATE TABLE statements (shippable)
│   ├── init_contacts.py   ← First-run: creates DB + schema + bootstraps first admin
│   ├── contacts.py        ← Python module (the API — all reads and writes)
│   ├── contacts.db        ← Live data (NOT shipped — created by init)
│   └── docs/
│       └── howto.md       ← Per-skill HOWTO (see docs/ below)
```

### What ships vs. what stays

| Ships (in repo) | Stays local |
|---|---|
| `schema.sql` | `contacts.db` (with real data) |
| `contacts.py` | Any cached exports |
| `init_contacts.py` | |
| `docs/howto.md` | |

The init script creates a fresh DB on install. Real data is never packaged.

---

## The pattern: functions are the API

```python
# contacts.py
from elko_contacts import get_contact, search, add, update_circle

# Check permissions first (every write function does this)
result = add("Pat Smith", "pat@example.com", requester_email="john@elko.ai")
if result.get("error"):
    print(f"Denied: {result['error']}")
else:
    print(f"Added contact {result['name']} (ID: {result['id']})")

# Reads are safe — no auth needed
pat = get_contact("pat@example.com")
```

Key conventions:

| Convention | Why |
|---|---|
| `ONE_DB` constant at top | Single source of truth for DB path |
| Every function has a docstring | Self-documenting API |
| Write functions check permissions first | Safety boundary — every mutation is guarded |
| Return dicts, never raw rows | Consistent interface, serializable |
| JSON columns for flexible fields | Capture anything; break out if queried relationally |
| DB path overridable via `ELKO_{NAME}_DB` | Test with separate DBs, deploy with production |

---

## Security model

Contacts has a permissions hierarchy:

```
super-admin      → Everything (add, edit, delete, grant)
contact-manager  → Add contacts, edit circles
viewer           → Read only
contact          → Can read themselves
```

Every write function checks the `requester_email` parameter against the permissions table. Reads are unauthenticated by design — they're safe by definition.

The init script prompts for a super-admin on first run. Without a super-admin, nothing works.

---

## Registry integration

Every elko-skill is registered in `elko-registry.db`:

```sql
-- Query: what elko-skills are available?
SELECT name, capability FROM services WHERE kind = 'elko-skill' AND active = 1;
```

The bootstrap injects the registry pointer into every session's system context, along with the "check registry first" reflex.

---

## Per-skill docs

Each elko-skill has a HOWTO in `docs/` covering:

- What it stores
- Key functions (with examples)
- Query patterns (how to get what you need)
- Common workflows
- Error handling

See `docs/` directory for individual skill documentation.

---

## Creating a new elko-skill

Use the template in `template/`:

```bash
cp -r template/ elko-skills/my-skill/
cd elko-skills/my-skill/
# Edit schema.sql, my_skill.py, init_my_skill.py
# Register in the registry
```

The template includes:
- `schema.sql` — starter schema with `meta` table (version tracking)
- `module.py` — stub with ONE_DB, connect, read/write patterns
- `init.py` — first-run DB creation

See `template/README.md` for a step-by-step walkthrough.

---

## Marketplace export

To package an elko-skill for redistribution:

1. Copy the directory
2. Remove `*.db` files (never ship data)
3. Run `init_*.py` on install — it creates a fresh DB
4. Ship as a GitHub repo or marketplace package (Smithery, PulseMCP, etc.)

The init script handles first-run setup. No config files to edit.

---

## Roadmap

- [x] Contacts (people, permissions, platforms)
- [x] Threads (cross-channel conversation tracking)
- [ ] Credentials (API keys, tokens, secrets — never exported)
- [ ] Audit log (timestamped action records)
- [ ] MCP server wrapper (same functions, MCP transport)
- [ ] Hermes native skill integration (auto-load from registry)

---

## License

MIT — elko.ai
