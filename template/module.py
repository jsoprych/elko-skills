#!/usr/bin/env python3
"""
hs-template — Elko-Skill Module
Template for creating new elko-skills.
Fill in the read/write functions with your domain logic.

Relies on elko_util.ElkoSkill for DB lifecycle and safe_update/safe_insert
for SQL injection defense. Every elko-skill follows this pattern.
"""
import sqlite3, os, json

from elko_util import ElkoSkill, safe_update, safe_insert, is_super_admin

# ── Schema (inline — single source of truth) ───────────────
SCHEMA = """\
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
INSERT INTO meta (key, value) VALUES ('version', '1.0.0');
INSERT INTO meta (key, value) VALUES ('description', 'Replace with your skill description');

CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    value TEXT,
    metadata TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_records_name ON records(name);
"""

# ── Skill singleton ────────────────────────────────────────
_skill = ElkoSkill(
    name='template',
    env_var='ELKO_TEMPLATE_DB',
    default_db_filename='template.db',
    schema_sql=SCHEMA,
)

# ── Allowed columns (whitelist for safe_update/safe_insert) ─
_RECORD_COLUMNS = {'name', 'value', 'metadata'}


# ═══════════════════════════════════════════════════════════
# READ functions — safe, no auth needed
# ═══════════════════════════════════════════════════════════

def get(id):
    """Get a single record by ID. Returns dict or None.
    
    Safe: ? placeholder for id value.
    """
    return _skill.query_one("SELECT * FROM records WHERE id = ?", (id,))


def search(term):
    """Search records by name (partial match). Returns list of dicts.
    
    Safe: LIKE value uses ? placeholder.
    """
    return _skill.query_all(
        "SELECT * FROM records WHERE name LIKE ?",
        (f'%{term}%',)
    )


def list_all(offset=0, limit=50):
    """List all records with pagination."""
    return _skill.query_all(
        "SELECT * FROM records ORDER BY updated_at DESC LIMIT ? OFFSET ?",
        (limit, offset)
    )


# ═══════════════════════════════════════════════════════════
# WRITE functions — permission check required
# ═══════════════════════════════════════════════════════════

def add(name, value, requester_email, metadata=None):
    """Add a new record. Requires contact-manager or higher.
    
    SQL injection defense: uses safe_insert() from elko_util.
    All values passed as ? placeholders.
    """
    conn = _skill.connect()
    
    if not is_super_admin(conn, requester_email):
        conn.close()
        return {"error": f"Permission denied. {requester_email} is not super-admin."}
    
    try:
        sql, params = safe_insert('records', {
            'name': name,
            'value': value,
            'metadata': json.dumps(metadata or {}),
        }, _RECORD_COLUMNS)
    except ValueError as e:
        conn.close()
        return {"error": str(e)}
    
    cursor = conn.execute(sql, params)
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    
    return {"success": True, "id": new_id, "name": name}


def update_record(id, requester_email, **kwargs):
    """Update a record. Only super-admin can update.
    
    SQL injection defense: uses safe_update() from elko_util.
    Column names validated against _RECORD_COLUMNS whitelist.
    All values passed as ? placeholders.
    """
    conn = _skill.connect()
    
    if not is_super_admin(conn, requester_email):
        conn.close()
        return {"error": "Permission denied. Only super-admin can update records."}
    
    updates = dict(kwargs)
    if 'metadata' in updates and isinstance(updates['metadata'], dict):
        updates['metadata'] = json.dumps(updates['metadata'])
    
    try:
        sql, params = safe_update('records', updates, 'id = ?', [id], _RECORD_COLUMNS)
    except ValueError as e:
        conn.close()
        return {"error": str(e)}
    
    conn.execute(sql, params)
    conn.commit()
    conn.close()
    
    return {"success": True, "id": id, "updated": [k for k in kwargs if k in _RECORD_COLUMNS]}


def delete(id, requester_email):
    """Delete a record. Super-admin only."""
    conn = _skill.connect()
    
    if not is_super_admin(conn, requester_email):
        conn.close()
        return {"error": "Permission denied. Only super-admin can delete records."}
    
    conn.execute("DELETE FROM records WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    
    return {"success": True, "deleted_id": id}


# ═══════════════════════════════════════════════════════════
# UTILITY
# ═══════════════════════════════════════════════════════════

def summary():
    """Return quick stats about this skill."""
    conn = _skill.connect()
    total = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    conn.close()
    return {
        "skill": "template",
        "total_records": total,
        "db_path": _skill.db_path,
    }
