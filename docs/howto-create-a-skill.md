# How to Create an Elko-Skill

A step-by-step walkthrough for building a new elko-skill from scratch. Use this when you want to add a new structured data domain to the agent — credentials, audit logs, bookmarks, notes, whatever.

---

## Prerequisites

- Python 3.8+ (sqlite3 is built-in)
- The elko-skills pattern is already set up (`/opt/data/elko-skills/`)
- A registry DB exists (`elko-registry.db` with a `services` table)

---

## Step 1: Plan the schema

Before writing any code, decide:

| Question | Example |
|---|---|
| What is this skill's single responsibility? | Track API credentials |
| What tables do you need? | `credentials`, `credential_scopes` |
| What are the always-queried columns? | `service_name`, `api_key_encrypted` |
| What's flexible/unpredictable? → JSON column | `metadata` (rate limits, expiry notes) |
| Who should be able to write? | Super-admin only |
| Who should be able to read? | Super-admin, contact-manager, or the credential owner |

---

## Step 2: Create the directory

```bash
mkdir -p elko-skills/credentials/
cd elko-skills/credentials/
```

---

## Step 3: Write schema.sql

```sql
-- Every elko-skill should track its own version
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
INSERT INTO meta (key, value) VALUES ('version', '1.0.0');
INSERT INTO meta (key, value) VALUES ('description', 'API credentials and secrets');

-- Your data tables
CREATE TABLE IF NOT EXISTS credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    owner_email TEXT,
    scopes TEXT DEFAULT '[]',          -- JSON array: ["read", "write"]
    metadata TEXT DEFAULT '{}',        -- JSON object: flexible fields
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS credential_scopes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    credential_id INTEGER NOT NULL REFERENCES credentials(id),
    scope TEXT NOT NULL
);

CREATE INDEX idx_credential_service ON credentials(service_name);
```

**Rules:**
- `meta` table is standard for every elko-skill (version tracking)
- JSON columns for anything you won't query in WHERE clauses
- Break out to separate tables for anything you will filter or join on
- Use `TEXT` for dates (SQLite has no native date type — functions work fine)

---

## Step 4: Write the module (credentials.py)

```python
#!/usr/bin/env python3
"""hs-credentials — Elko-Skill Module
API credentials storage. Encrypted at rest. Never exported.
"""
import sqlite3, os, json

# Path resolution (same pattern for every elko-skill)
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
ONE_DB = os.environ.get('ELKO_CREDENTIALS_DB', os.path.join(SKILL_DIR, 'credentials.db'))

def _connect():
    """Get a connection. Called by every function — never exposed."""
    return sqlite3.connect(ONE_DB)

# ── Reads (safe — no auth) ──────────────────────────────────

def get_credentials(service_name=None, owner_email=None):
    """List credentials, optionally filtered by service or owner."""
    conn = _connect()
    conn.row_factory = sqlite3.Row
    # ... query logic ...
    return [dict(r) for r in rows]

# ── Writes (must check permissions) ─────────────────────────

def add(service_name, api_key, requester_email, metadata=None):
    """Add a credential. Super-admin only."""
    conn = _connect()
    
    # Permission check — every write starts with this
    cursor = conn.execute(
        "SELECT user_role FROM contact_auth WHERE contact_email = ?",
        (requester_email,)
    )
    row = cursor.fetchone()
    if not row or row[0] != 'super-admin':
        return {"error": f"Permission denied: {requester_email} is not super-admin"}
    
    # Proceed with the write
    conn.execute("INSERT INTO credentials (...) VALUES (...)", ...)
    conn.commit()
    return {"success": True, "id": cursor.lastrowid}
```

**Every write function MUST:**
1. Check permissions first
2. Return a dict (success or error)
3. Commit the transaction
4. Have a clear docstring

---

## Step 5: Write init_credentials.py

```python
#!/usr/bin/env python3
"""hs-credentials — Initializer (Elko-Skill)
First-run setup. Creates the DB from schema.sql if it doesn't exist.
"""
import sqlite3, os, sys

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('ELKO_CREDENTIALS_DB', os.path.join(SKILL_DIR, 'credentials.db'))
SCHEMA_PATH = os.path.join(SKILL_DIR, 'schema.sql')

def init():
    if os.path.exists(DB_PATH):
        print(f"DB already exists: {DB_PATH}")
        return
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"Created: {DB_PATH}")

if __name__ == '__main__':
    init()
```

---

## Step 6: Write docs/howto.md

Every elko-skill needs a HOWTO covering:

- What it stores
- Key functions with real examples
- Common SQL queries
- Permission model
- Error messages

See `contacts/docs/howto.md` and `threads/docs/howto.md` for examples.

---

## Step 7: Register in the registry

```sql
INSERT INTO services (name, kind, path, capability, summary_query, active)
VALUES (
    'hs-credentials',
    'elko-skill',
    '/opt/data/elko-skills/credentials',
    'store, retrieve, and manage API credentials with encryption',
    'SELECT COUNT(*) || '' credentials stored'' FROM credentials',
    1
);
```

---

## Step 8: Run the init

```bash
python3 elko-skills/credentials/init_credentials.py
```

---

## Skill checklist

- [ ] schema.sql has a `meta` table with version
- [ ] Module has `ONE_DB` constant
- [ ] Module has `_connect()` helper
- [ ] Every read function returns dicts
- [ ] Every write function checks permissions
- [ ] Init script creates DB on first run (idempotent)
- [ ] DB path overridable via `ELKO_{NAME}_DB` env var
- [ ] HOWTO covers what, how, and common queries
- [ ] Registered in the registry
- [ ] Tested: import the module, call a read function
