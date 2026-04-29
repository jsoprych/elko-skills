# elko-skills on Hermes Agent

Hermes is the native platform. Two integration paths: **MCP server** (recommended for all agents) and **direct Python import** (Hermes-native, deepest integration).

---

## MCP setup (recommended)

Same as any other platform — auto-detected by `install_mcp.py`:

```bash
python3 install_mcp.py contacts
python3 install_mcp.py threads
```

Or add to your Hermes MCP config manually:

```json
{
  "mcpServers": {
    "elko-contacts": {
      "command": "uvx",
      "args": ["elko-contacts"],
      "env": { "ELKO_SUPER_ADMIN_EMAIL": "you@example.com" }
    },
    "elko-threads": {
      "command": "uvx",
      "args": ["elko-threads"]
    }
  }
}
```

`ELKO_SUPER_ADMIN_EMAIL` seeds the first super-admin on startup. No manual DB init needed.

---

## Direct Python import (Hermes-native)

### One-liner install

```bash
./install.sh contacts
./install.sh threads
```

The installer detects Hermes from `HERMES_DATA_DIR` or `~/.hermes/config.yaml` and auto-registers in `elko-registry.db`.

### Manual setup

**1. Clone**

```bash
git clone https://github.com/jsoprych/elko-skills.git /opt/data/elko-skills
```

**2. Init DBs**

```bash
cd /opt/data/elko-skills
ELKO_CONTACTS_DB=/opt/data/elko-skills/contacts/contacts.db python3 contacts/init_contacts.py
ELKO_THREADS_DB=/opt/data/elko-skills/threads/threads.db   python3 threads/init_threads.py
```

**3. Seed super-admin**

```bash
ELKO_CONTACTS_DB=/opt/data/elko-skills/contacts/contacts.db python3 -c "
from contacts import contacts
print(contacts.bootstrap('you@example.com'))
"
```

**4. Register in elko-registry**

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

**5. Add to startup.py / bootstrap card**

```python
import sys
sys.path.insert(0, '/opt/data/elko-skills')
from contacts import contacts
from threads import threads
```

---

## Usage in Hermes (direct import)

```python
from contacts import contacts
from threads import threads

# Reads — no auth needed
contacts.list_all()
contacts.get_by_email('john@elko.ai')
contacts.find('john')
contacts.check_is_super_admin('john@elko.ai')

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

Every session prints:

```
╔══════════════════════════════════════════════════════════╗
║                    ELKO-SKILLS                          ║
╠══════════════════════════════════════════════════════════╣
║  elko-contacts  → 5 contacts (1 admin, 2 family)       ║
║  elko-threads   → 8 threads (5 active), 34 messages    ║
╚══════════════════════════════════════════════════════════╝
```

---

## Env var configuration

```bash
export ELKO_CONTACTS_DB=/opt/data/elko-skills/contacts/contacts.db
export ELKO_THREADS_DB=/opt/data/elko-skills/threads/threads.db
export ELKO_SUPER_ADMIN_EMAIL=you@example.com   # auto-seeds admin on first MCP start
```

---

## Sandbox install

```bash
python3 install_mcp.py contacts --sandbox
python3 install_mcp.py threads  --sandbox
# All DBs in ~/.elko-sandbox/  —  purge: rm -rf ~/.elko-sandbox
```

---

## Testing

```bash
cd /opt/data/elko-skills
python3 -m pytest contacts/tests threads/tests -q
```
