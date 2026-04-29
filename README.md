# elko-skills

**Database-backed, self-initializing structured skills for AI agents.**

An elko-skill is a reusable building block: one Python module wrapping one SQLite database, registered in a global directory, and discoverable at runtime. Every elko-skill is self-contained — create a DB, ship the schema, import the module, call the functions.

```
elko-skill = Python module + SQLite DB + registry entry
```

---

## Quick start

```bash
# One command, any platform
git clone https://github.com/jsoprych/elko-skills.git
cd elko-skills
./install.sh contacts          # interactive
./install.sh threads           # interactive
```

Or platform-specific:

| Platform | Install | Import |
|---|---|---|
| **Hermes** | `./install.sh contacts` | `from contacts import contacts as hs` |
| **Claude Code** | Add to CLAUDE.md | `python3 contacts/contacts.py` |
| **Codex CLI** | Add to `.codex/config.yaml` | `import contacts` |
| **OpenClaw** | `pip install -e .` | `import contacts` |
| **OpenCode** | Add to `.opencode/skills.yaml` | skill binding |

See [`docs/platforms/`](docs/platforms/) for full setup guides.

---

## Platform matrix

| Feature | Hermes | Claude Code | Codex CLI | OpenClaw | OpenCode |
|---|---|---|---|---|---|
| Python import | ✅ native | ✅ CLAUDE.md | ✅ config | ✅ native | ✅ config |
| Auto-registry | ✅ | — | — | — | — |
| Bootstrap card | ✅ | — | — | — | — |
| ACP bridge | — | ✅ | — | — | — |
| Tool binding | — | ✅ | ✅ | ✅ | ✅ |
| SQL injection defense | ✅ all | ✅ all | ✅ all | ✅ all | ✅ all |
| Permission model | ✅ | ✅ | ✅ | ✅ | ✅ |
| Tests | 70 ✓ | 70 ✓ | 70 ✓ | 70 ✓ | 70 ✓ |

---

## Why elko-skills?

AI agents (Hermes, Claude Code, Codex, OpenClaw, OpenCode) have no built-in user database, contact system, or permissions model. They operate per-session with no persistent state. elko-skills fill that gap — they give agents:

- **Persistent state** — survive across restarts, sessions, and agents
- **Structured access** — Python functions wrap raw SQL; the function is the API
- **Permissions** — write operations check authorization before touching data
- **Discoverability** — the registry tells every agent what data is available
- **Marketplace-ready** — ship module + init script; data stays local

---

## Built skills

| Skill | What | Tests | Docs | Platform setup |
|---|---|---|---|---|
| **hs-contacts** | People, permissions, platforms | 41 ✓ | [howto](contacts/docs/howto.md) | [all](docs/platforms/) |
| **hs-threads** | Cross-channel conversation tracking | 29 ✓ | [howto](threads/docs/howto.md) | [all](docs/platforms/) |
| **elko_util** | Core library — ElkoSkill, safe_update, permission checks | — | docstrings | shared |

### hs-contacts

```python
from contacts import contacts as hs

# Reads (no auth needed)
hs.list_all()                                              # all contacts
hs.get_by_email('john@elko.ai')                            # one contact + phones + platforms
hs.find('john')                                            # fuzzy search
hs.check_is_super_admin('john@elko.ai')                    # permission check
hs.get_permissions('diana@example.com')                    # their auth rules

# Writes (every one checks requester_email)
hs.add('Pat Smith', 'pat@example.com', requester_email='john@elko.ai')
hs.update('pat@example.com', 'john@elko.ai', circle='work')
hs.grant('pat@example.com', 'email.send', requester_email='john@elko.ai')
```

### hs-threads

```python
from threads import threads as t

t.active()                                                 # active threads, newest first
t.capture('AI-World-Daily', 'email', msg, participants=['john@elko.ai'])
t.context('AI-World-Daily')                                # full message history
t.tag('AI-World-Daily', 'important')                       # tag for filtering
t.summary()                                                # "8 threads (5 active), 34 messages"
```

---

## The pattern: functions are the API

```python
from elko_util import ElkoSkill, safe_update

_skill = ElkoSkill(name='contacts', env_var='ELKO_CONTACTS_DB', ...)

# Read —  one line via the core library
def list_all():
    return _skill.query_all("SELECT ...")

# Write — permission check, then safe_update
def update(email, requester_email, **kwargs):
    if not is_super_admin(conn, requester_email):
        return {"error": "Permission denied."}
    sql, params = safe_update('contacts', kwargs, 'email = ?', [email], ALLOWED_COLUMNS)
    conn.execute(sql, params)
```

Key conventions:

| Convention | Why |
|---|---|
| Every function returns dicts | Consistent interface, serializable |
| Write functions check permissions first | Safety boundary — every mutation is guarded |
| `safe_update` validates column whitelist | SQL injection defense line 2 |
| `?` placeholders for all values | SQL injection defense line 1 |
| JSON columns for flexible fields | Capture anything; break out if queried relationally |
| DB path overridable via `ELKO_{NAME}_DB` | Test with separate DBs, deploy with production |

---

## Security

**Two-layer defense against SQL injection:**

1. **All values** go through `?` parameterized placeholders — never string-interpolated
2. **All column names** validated against a whitelist — `safe_update()` accepts only known columns

And 5 dedicated injection-resistance tests:

```python
# A name like this is stored literally, never executed:
"Robert'); DROP TABLE contacts; --"
hs.update('alice@example.com', 'admin@elko.ai', name=dangerous_name)
# → contacts table still exists, name is stored verbatim
```

Every write function checks `requester_email` against the permissions table.
Reads are safe by design — no auth needed.

---

## Architecture

```
startup.py
  └─► bootstrap.db        ← Identity + reflexes
         └─► elko-registry.db    ← Pure directory (services table only)
                ├─► elko-skills/contacts/    ← contacts.py + contacts.db
                └─► elko-skills/threads/     ← threads.py + threads.db
```

**Three layers:**
1. **Bootstrap** — Identity, registry pointer, and learned reflexes
2. **Registry** — Pure directory. No data lives here.
3. **Elko-skill** — The module. The schema. The functions. The data.

---

## What ships vs. what stays

| Ships (in repo) | Stays local |
|---|---|
| `contacts.py` | `contacts.db` (with real data) |
| `init_contacts.py` | Any cached exports |
| `docs/howto.md` | |
| `tests/test_contacts.py` | |

The init script creates a fresh DB on install. Real data is never packaged.

---

## Creating a new elko-skill

```bash
cp -r template/ elko-skills/my-skill/
cd elko-skills/my-skill/
# Edit schema.sql, module.py, init.py
# Set env var: export ELKO_MYSKILL_DB=/path/to/db
# Init:        python3 init_myskill.py
# Test:        python3 -m pytest tests/
# Register:    python3 -c "..."  (see docs/platforms/hermes.md)
# Ship:        git add, commit, push
```

See [`template/`](template/), [`docs/howto-create-a-skill.md`](docs/howto-create-a-skill.md), and the [platform setup guides](docs/platforms/).

---

## Roadmap

### Built ✅
- [x] **hs-contacts** — people, permissions, platforms (41 tests)
- [x] **hs-threads** — cross-channel conversation tracking (29 tests)
- [x] **elko_util** — core library, safe SQL builders, ElkoSkill base class
- [x] **Universal installer** — `install.sh` works on all 5 platforms
- [x] **Platform setup docs** — Hermes, Claude Code, Codex CLI, OpenClaw, OpenCode
- [x] **Template** — starter kit for new elko-skills
- [x] **Registry** — elko-registry.db service directory

### Next 🔨
- [ ] **hs-credentials** — API keys, tokens, secrets (encrypted at rest)
- [ ] **hs-audit-log** — timestamped action records for all skills
- [ ] **hs-email-threads** — Message-ID threading, inbox tracking
- [ ] **hs-blog-pipeline** — draft → review → publish lifecycle
- [ ] **hs-ai-world-kg** — AI industry knowledge graph as an elko-skill

### Future 🚀
- [ ] MCP server wrapper (same functions, MCP transport)
- [ ] Smithery / PulseMCP marketplace packages
- [ ] elko-foundry architecture

---

## Directory structure

```
elko-skills/
├── install.sh              ← Universal installer (all platforms)
├── elko_util.py            ← Core library: ElkoSkill, safe_update, is_super_admin
├── README.md               ← You are here
├── .gitignore
├── run_tests.py
├── contacts/
│   ├── contacts.py         ← Module (the API)
│   ├── init_contacts.py    ← First-run DB creation
│   ├── schema.sql          ← CREATE TABLE statements
│   ├── docs/howto.md       ← Usage guide
│   └── tests/test_contacts.py  ← 41 tests
├── threads/
│   ├── threads.py          ← Module (the API)
│   ├── init_threads.py     ← First-run DB creation
│   ├── schema.sql          ← CREATE TABLE statements
│   ├── docs/howto.md       ← Usage guide
│   └── tests/test_threads.py   ← 29 tests
├── template/               ← Starter kit for new elko-skills
│   ├── module.py
│   ├── init.py
│   ├── schema.sql
│   ├── docs/howto.md
│   └── tests/test_template.py
├── docs/
│   ├── README.md
│   ├── howto-create-a-skill.md
│   └── platforms/
│       ├── README.md
│       ├── hermes.md
│       ├── claude-code.md
│       ├── codex.md
│       ├── openclaw.md
│       └── opencode.md
└── run_tests.py            ← One command to run all tests
```

---

## License

MIT — elko.ai
