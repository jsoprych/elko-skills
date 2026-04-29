# elko-skills Template

Copy this directory to create a new elko-skill:

```bash
cp -r template/ elko-skills/my-skill-name/
```

Then fill in the four files:

1. **schema.sql** — your data model
2. **module.py** → rename to `my_skill.py** — Python API
3. **init.py** → rename to `init_my_skill.py** — first-run setup
4. **docs/howto.md** — documentation

---

## Files

### schema.sql

```sql
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
INSERT INTO meta (key, value) VALUES ('version', '1.0.0');
INSERT INTO meta (key, value) VALUES ('description', 'Description of this skill');

-- Your tables here
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    value TEXT,
    metadata TEXT DEFAULT '{}',       -- JSON for flexible fields
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
```

### module.py

Rename to match your skill name. Every elko-skill follows the same pattern:

- `ONE_DB` constant
- `_connect()` helper
- Read functions: return dicts, no auth needed
- Write functions: check permissions, return dicts
- `summary()` function: quick stats

### init.py

Rename to `init_<skill_name>.py`. Creates the DB from schema.sql on first run.

### docs/howto.md

Documentation for users and agents who need to query this skill.
