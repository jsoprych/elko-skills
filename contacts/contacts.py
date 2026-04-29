#!/usr/bin/env python3
"""
elko-hs-contacts — Elko-Skill Module
Single source of truth for people. Wraps a SQLite DB with a permissions model.
Every write function checks permissions. Every read function is safe.

Relies on elko_util.ElkoSkill for DB lifecycle and safe_update/safe_insert
for SQL injection defense. No raw SQL string-building with user data.

Usage:
    from elko_hs_contacts import contacts
    contacts.list_all()                     → [{id, name, email, circle, role}]
    contacts.find('john')                   → fuzzy search
    contacts.add(name, email, requester)    → checks requester is super-admin
"""
import sqlite3, json, os

from elko_util import ElkoSkill, safe_update, is_super_admin

# ── Schema (inline — single source of truth) ───────────────
SCHEMA = """\
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, email TEXT UNIQUE, role TEXT DEFAULT 'contact',
    circle TEXT DEFAULT 'family', discretion TEXT DEFAULT 'public',
    metadata TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS contact_phones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER REFERENCES contacts(id), label TEXT, number TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS contact_platforms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER REFERENCES contacts(id),
    platform TEXT NOT NULL, platform_id TEXT NOT NULL, label TEXT DEFAULT 'primary',
    UNIQUE(contact_id, platform)
);
CREATE TABLE IF NOT EXISTS auth_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER REFERENCES contacts(id),
    permission TEXT NOT NULL, scope TEXT DEFAULT '*',
    UNIQUE(contact_id, permission)
);
"""

# ── Skill singleton ────────────────────────────────────────
_skill = ElkoSkill(
    name='contacts',
    env_var='ELKO_CONTACTS_DB',
    default_db_filename='contacts.db',
    schema_sql=SCHEMA,
)

# ── Allowed columns (whitelist for safe_update) ────────────
_CONTACT_COLUMNS = {'name', 'email', 'circle', 'role', 'discretion', 'metadata'}


def _connect():
    return _skill.connect()


# ═══════════════════════════════════════════════════════════
# READERS (safe, no permission check)
# ═══════════════════════════════════════════════════════════

def list_all():
    """Return all contacts as a list of dicts."""
    return _skill.query_all("""
        SELECT id, name, email, COALESCE(circle,'') as circle,
               COALESCE(role,'') as role, COALESCE(discretion,'public') as discretion,
               COALESCE(metadata,'{}') as metadata
        FROM contacts ORDER BY name
    """)


def get_by_email(email):
    """Get a single contact by email. Returns dict or None.
    
    Safe: ? placeholder for email value.
    """
    conn = _connect()
    conn.row_factory = sqlite3.Row
    
    row = conn.execute("SELECT * FROM contacts WHERE email = ?", (email,)).fetchone()
    if not row:
        conn.close()
        return None
    
    result = dict(row)
    result['phones'] = [dict(r) for r in conn.execute(
        "SELECT id, label, number FROM contact_phones WHERE contact_id = ?", (result['id'],)).fetchall()]
    result['platforms'] = [dict(r) for r in conn.execute(
        "SELECT id, platform, platform_id, label FROM contact_platforms WHERE contact_id = ?", (result['id'],)).fetchall()]
    conn.close()
    return result


def find(query):
    """Fuzzy search by name or email. Returns list.
    
    Safe: LIKE value uses ? placeholder — user data never reaches SQL string.
    """
    like = f"%{query}%"
    return _skill.query_all("""
        SELECT id, name, email, circle, role FROM contacts
        WHERE name LIKE ? OR email LIKE ?
        ORDER BY name LIMIT 20
    """, (like, like))


def has_permission(email, permission):
    """Check if a contact has a specific permission granted."""
    conn = _connect()
    cid = conn.execute("SELECT id FROM contacts WHERE email = ?", (email,)).fetchone()
    if not cid:
        conn.close()
        return False
    row = conn.execute("""
        SELECT id FROM auth_rules
        WHERE contact_id = ? AND permission = ? AND (scope = '*' OR scope = 'self')
    """, (cid[0], permission)).fetchone()
    conn.close()
    return row is not None


def check_is_super_admin(email):
    """Check if a contact has super-admin role. Convenience wrapper.
    
    Safe: parameterized query, ? placeholder for email.
    """
    conn = _connect()
    result = is_super_admin(conn, email)
    conn.close()
    return result


def get_permissions(email):
    """Get all permissions for a contact. Returns list of {permission, scope}."""
    return _skill.query_all(
        "SELECT permission, scope FROM auth_rules WHERE contact_id = (SELECT id FROM contacts WHERE email = ?)",
        (email,)
    )


# ═══════════════════════════════════════════════════════════
# WRITERS (permission check required)
# ═══════════════════════════════════════════════════════════

def add(name, email, requester_email, circle=None, role='contact', phone=None, platforms=None):
    """Add a new contact. Only super-admin can add.
    
    Returns dict with success or error.
    Safe: all user values passed as ? placeholders.
    """
    conn = _connect()
    
    if not is_super_admin(conn, requester_email):
        conn.close()
        return {"error": f"Permission denied. {requester_email} is not super-admin."}
    
    existing = conn.execute("SELECT id FROM contacts WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        return {"error": f"Contact {email} already exists."}
    
    conn.execute(
        "INSERT INTO contacts (name, email, circle, role, discretion, metadata) VALUES (?, ?, ?, ?, 'public', '{}')",
        (name, email, circle or 'family', role)
    )
    cid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    if phone:
        conn.execute(
            "INSERT INTO contact_phones (contact_id, label, number) VALUES (?, 'mobile', ?)",
            (cid, phone)
        )
    
    if platforms:
        for p in platforms:
            conn.execute(
                "INSERT OR IGNORE INTO contact_platforms (contact_id, platform, platform_id, label) VALUES (?, ?, ?, ?)",
                (cid, p['platform'], p['id'], p.get('label', 'primary'))
            )
    
    if role != 'super-admin':
        for perm in ['email.send', 'email.receive']:
            conn.execute(
                "INSERT OR IGNORE INTO auth_rules (contact_id, permission, scope) VALUES (?, ?, 'self')",
                (cid, perm)
            )
    
    conn.commit()
    conn.close()
    return {"success": True, "id": cid, "email": email, "name": name}


def grant(email, permission, scope='*', requester_email=None):
    """Grant a permission to a contact. Only super-admin."""
    conn = _connect()
    
    if not requester_email or not is_super_admin(conn, requester_email):
        conn.close()
        return {"error": "Permission denied."}
    
    cid = conn.execute("SELECT id FROM contacts WHERE email = ?", (email,)).fetchone()
    if not cid:
        conn.close()
        return {"error": f"Contact {email} not found."}
    
    conn.execute(
        "INSERT OR IGNORE INTO auth_rules (contact_id, permission, scope) VALUES (?, ?, ?)",
        (cid[0], permission, scope)
    )
    conn.commit()
    conn.close()
    return {"success": True, "email": email, "permission": permission}


def update(email, requester_email, **kwargs):
    """Update contact fields. Only super-admin.
    
    SQL injection defense: uses safe_update() from elko_util which:
      1. Validates column names against _CONTACT_COLUMNS whitelist
      2. Passes all values as ? placeholders
      3. Appends updated_at = datetime('now') automatically
    """
    conn = _connect()
    
    if not is_super_admin(conn, requester_email):
        conn.close()
        return {"error": "Permission denied. Only super-admin can update contacts."}
    
    # Serialize metadata dicts before building SQL
    updates = dict(kwargs)
    if 'metadata' in updates and isinstance(updates['metadata'], dict):
        updates['metadata'] = json.dumps(updates['metadata'])
    
    try:
        sql, params = safe_update('contacts', updates, 'email = ?', [email], _CONTACT_COLUMNS)
    except ValueError as e:
        conn.close()
        return {"error": str(e)}
    
    conn.execute(sql, params)
    conn.commit()
    conn.close()
    
    updated = [k for k in kwargs if k in _CONTACT_COLUMNS]
    return {"success": True, "updated": updated}


# ═══════════════════════════════════════════════════════════
# UTILITY
# ═══════════════════════════════════════════════════════════

def summary():
    """One-liner for bootstrap card."""
    conn = _connect()
    total = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
    admins = conn.execute("SELECT COUNT(*) FROM contacts WHERE role = ?", ('super-admin',)).fetchone()[0]
    family = conn.execute("SELECT COUNT(*) FROM contacts WHERE circle = ?", ('family',)).fetchone()[0]
    conn.close()
    return f"{total} contacts ({admins} admin, {family} family)"


if __name__ == "__main__":
    print("=== CONTACTS ELKO-SKILL TEST ===")
    print(f"Summary: {summary()}")
    print("\nAll contacts:")
    for c in list_all():
        print(f"  [{c['role']:12s}] {c['name']:20s} <{c['email']:35s}> {c['circle']}")
