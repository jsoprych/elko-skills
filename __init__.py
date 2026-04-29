# ============================================================
# ELKO-SKILL PATTERN — The elko.ai Way
# ============================================================
# Location: /opt/data/elko-skills/__init__.py
# Registry query: SELECT name, capability FROM elko-registry.db.services WHERE kind='elko-skill'
# Boot card: startup.py displays active elko-skills from registry
#
# An elko-skill is:
#   One Python module  →  One SQLite DB  →  One registry entry
#
# The module wraps the DB as Python functions (stored procedures).
# The SQL is an implementation detail — transparent to the caller.
# The functions ARE the API, and the same API can later be served as an MCP server.
# ============================================================

1. BOOT CARD → tells me which elko-skills are registered and active
2. REGISTRY QUERY → SELECT name, capability FROM services WHERE kind='elko-skill'
3. import the module → call the functions

Structure:
|   /opt/data/elko-skills/
    ├── __init__.py          ← This file (pattern documentation)
    ├── contacts/
    │   ├── schema.sql       ← CREATE TABLE statements
    │   ├── init_contacts.py ← First-run: creates DB, prompts for super-admin
    │   ├── contacts.py      ← Python module (stored procedures)
    │   └── contacts.db      ← Live data (NOT shipped)
    ├── threads/
    │   ├── schema.sql       ← CREATE TABLE statements
    │   ├── init_threads.py  ← First-run: creates DB
    │   ├── threads.py       ← Python module (stored procedures)
    │   └── threads.db       ← Live data (NOT shipped)
    └── ...                  ← More elko-skills as needed

Elko-skill naming conventions:
  - Module name = service name (snake_case)
  - ONE_DB constant at top of module
  - Every function has a docstring
  - Write functions check permissions first
  - Return dicts, never raw rows
  - JSON columns for unpredictable fields
  - Break out to columns/tables when you query them relationally
  - DB path overridable via ELKO_{NAME}_DB env var

Export to other agents / marketplace:
  Package structure: schema.sql + module + empty DB stub + init script.
  Real data stays local — never ships. Init script creates fresh DB on install.
  A future MCP server can wrap the same module. The functions stay the same;
  only the transport changes.
