# elko-skills on Hermes Agent

Hermes is the native platform. Three integration paths, ordered by simplicity:

| Path | Best for |
|------|----------|
| [Python subprocess (MCP)](#mcp-python-subprocess) | **Primary** — runs inside Hermes container, uses `/data/elko/` directly |
| [Docker container (MCP)](#mcp-docker-container) | If you prefer isolated containers per skill |
| [Direct Python import](#direct-python-import) | Deepest integration, bootstrap card, registry |

---

## MCP — Python subprocess (recommended) {#mcp-python-subprocess}

Runs elko-skills as a Python subprocess **inside** the Hermes container. Hermes already owns `/data` as uid 10000 — no volume mounting, no UID negotiation, no Docker socket needed.

### One-time setup (inside Hermes container or in Hermes Dockerfile)

```bash
git clone https://github.com/jsoprych/elko-skills.git /opt/elko-skills
pip install fastmcp
mkdir -p /data/elko
```

### Hermes MCP config

```yaml
mcpServers:
  elko-contacts:
    command: python3
    args:
      - /opt/elko-skills/contacts/mcp_server.py
    env:
      ELKO_DATA_DIR: /data/elko
      ELKO_SUPER_ADMIN_EMAIL: "you@example.com"

  elko-threads:
    command: python3
    args:
      - /opt/elko-skills/threads/mcp_server.py
    env:
      ELKO_DATA_DIR: /data/elko
```

`ELKO_DATA_DIR=/data/elko` puts all skill DBs under Hermes's `/data/elko/`:

```
/data/elko/
  contacts.db    ← owned by hermes (uid 10000) ✓
  threads.db     ← owned by hermes (uid 10000) ✓
```

`ELKO_SUPER_ADMIN_EMAIL` seeds the first super-admin on startup. No manual DB init needed.

### Verify

```bash
python3 /opt/elko-skills/install_mcp.py --inspect
```

---

## MCP — Docker container {#mcp-docker-container}

Each skill runs as an independent Docker container over stdio. Requires Docker socket access from inside Hermes.

```yaml
mcpServers:
  elko-contacts:
    command: docker
    args:
      - run
      - -i
      - --rm
      - -u
      - "10000"
      - -e
      - ELKO_SUPER_ADMIN_EMAIL
      - -v
      - /opt/data/elko-skills:/data
      - ghcr.io/jsoprych/elko-contacts:latest
    env:
      ELKO_SUPER_ADMIN_EMAIL: "you@example.com"

  elko-threads:
    command: docker
    args:
      - run
      - -i
      - --rm
      - -u
      - "10000"
      - -v
      - /opt/data/elko-skills:/data
      - ghcr.io/jsoprych/elko-threads:latest
```

`-u 10000` matches Hermes's uid so the bind-mounted `/opt/data/elko-skills` is writable.

### Pre-release: local build

Until images are published to GHCR, build on the host:

```bash
git clone https://github.com/jsoprych/elko-skills.git
cd elko-skills
docker build -f contacts/Dockerfile -t ghcr.io/jsoprych/elko-contacts:latest .
docker build -f threads/Dockerfile  -t ghcr.io/jsoprych/elko-threads:latest  .
```

---

## Direct Python import {#direct-python-import}

Deepest Hermes integration — auto-registered in elko-registry, appears in bootstrap card.

### Setup

```bash
git clone https://github.com/jsoprych/elko-skills.git /opt/data/elko-skills
pip install fastmcp
```

### Register in elko-registry

```python
import sqlite3
db = sqlite3.connect('/opt/data/elko-registry.db')
db.execute("""
  INSERT OR IGNORE INTO services (name, kind, path, capability, summary_query, active)
  VALUES ('elko-contacts', 'elko-skill', '/opt/data/elko-skills/contacts',
          'people, permissions, platforms',
          'SELECT COUNT()||\" contacts\" FROM contacts', 1)
""")
db.execute("""
  INSERT OR IGNORE INTO services (name, kind, path, capability, summary_query, active)
  VALUES ('elko-threads', 'elko-skill', '/opt/data/elko-skills/threads',
          'cross-channel conversation tracking',
          'SELECT COUNT()||\" threads\" FROM threads', 1)
""")
db.commit()
```

### Add to startup.py

```python
import sys
sys.path.insert(0, '/opt/data/elko-skills')
from contacts import contacts
from threads import threads
```

### Seed super-admin (first run only)

```python
from contacts import contacts
contacts.bootstrap('you@example.com')
```

---

## Usage (direct import)

```python
from contacts import contacts
from threads import threads

# Reads — no auth needed
contacts.list_all()
contacts.find('john')
contacts.get_by_email('john@elko.ai')

# Writes — require requester_email of a super-admin
contacts.add('Diana', 'diana@example.com', requester_email='john@elko.ai')
contacts.update('diana@example.com', 'john@elko.ai', circle='friends')
contacts.grant('diana@example.com', 'email.send', requester_email='john@elko.ai')

# Threads
threads.active()
threads.capture('AI-World-Daily', 'email', msg, participants=['john@elko.ai'])
threads.context('AI-World-Daily')
threads.summary()
```

---

## Bootstrap card output

```
╔══════════════════════════════════════════════════════════╗
║                    ELKO-SKILLS                          ║
╠══════════════════════════════════════════════════════════╣
║  elko-contacts  → 5 contacts (1 admin, 2 family)       ║
║  elko-threads   → 8 threads (5 active), 34 messages    ║
╚══════════════════════════════════════════════════════════╝
```

---

## Env vars

| Var | Default | Purpose |
|-----|---------|---------|
| `ELKO_DATA_DIR` | — | All skill DBs land in `$ELKO_DATA_DIR/{skill}.db` |
| `ELKO_CONTACTS_DB` | `$ELKO_DATA_DIR/contacts.db` | Override contacts DB path |
| `ELKO_THREADS_DB` | `$ELKO_DATA_DIR/threads.db` | Override threads DB path |
| `ELKO_SUPER_ADMIN_EMAIL` | — | Seeds first super-admin on startup |

For Hermes: set `ELKO_DATA_DIR=/data/elko` and nothing else is needed.

---

## Diagnose

```bash
python3 /opt/elko-skills/install_mcp.py --inspect
```

Shows resolved DB paths, file status, permissions, and all active ELKO_* vars
for the current environment.

---

## Testing

```bash
cd /opt/elko-skills
python3 -m pytest contacts/tests threads/tests -q
```
