#!/usr/bin/env python3
"""
elko-hs-contacts — Elko-Skill Module

Single source of truth for people. Wraps a SQLite DB with a permissions model.
Every write function checks auth. Every read function uses the core library.

Zero code redundancy — all connection management, row-factory handling,
SQL safety, and permission checks come from elko_util.ElkoSkill.

Usage:
    from elko_hs_contacts import contacts
    contacts.list_all()                     → [{id, name, email, circle, role}]
    contacts.find('john')                   → fuzzy search
    contacts.add(name, email, requester)    → checks requester is super-admin

Security:
    - All queries use ? parameterized placeholders — no string interpolation
    - safe_update() validates column names against whitelist
    - Every write function checks :code:`is_super_admin()` first
"""
import json, os
from elko_util import ElkoSkill, safe_update


# ═══════════════════════════════════════════════════════════
# SCHEMA
# ═══════════════════════════════════════════════════════════

SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    role TEXT DEFAULT 'contact',
    circle TEXT DEFAULT 'family',
    discretion TEXT DEFAULT 'public',
    metadata TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS contact_phones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER REFERENCES contacts(id),
    label TEXT,
    number TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS contact_platforms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER REFERENCES contacts(id),
    platform TEXT NOT NULL,
    platform_id TEXT NOT NULL,
    label TEXT DEFAULT 'primary',
    UNIQUE(contact_id, platform)
);
CREATE TABLE IF NOT EXISTS auth_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER REFERENCES contacts(id),
    permission TEXT NOT NULL,
    scope TEXT DEFAULT '*',
    UNIQUE(contact_id, permission)
);
"""

# ── Singular skill instance ────────────────────────────────
_skill = ElkoSkill(
    name='contacts',
    env_var='ELKO_CONTACTS_DB',
    default_db_filename='contacts.db',
    schema_sql=SCHEMA,
)


def get_skill():
    """Return the underlying ElkoSkill instance.

    Used by tests and companion modules that need direct DB access.
    """
    return _skill

# ── Column whitelist (injection defence) ───────────────────
_CONTACT_COLUMNS = {'name', 'email', 'circle', 'role', 'discretion', 'metadata'}
_PHONE_COLUMNS = {'contact_id', 'label', 'number'}
_PLATFORM_COLUMNS = {'contact_id', 'platform', 'platform_id', 'label'}
_AUTH_COLUMNS = {'contact_id', 'permission', 'scope'}


# ═══════════════════════════════════════════════════════════
# READERS
#   All use _skill.query_all / query_one — no manual conn,
#   row_factory, fetch, or close anywhere.
# ═══════════════════════════════════════════════════════════

def list_all():
    """Return all contacts as a list of dicts."""
    return _skill.query_all("""
        SELECT id, name, email, COALESCE(circle,'') AS circle,
               COALESCE(role,'') AS role,
               COALESCE(discretion,'public') AS discretion,
               COALESCE(metadata,'{}') AS metadata
        FROM contacts ORDER BY name
    """)


def get_by_email(email):
    """Get a single contact by email. Returns dict or None.

    Also fetches phones and platforms. Uses a manual connection because
    we need multiple queries in one transaction.
    """
    conn = _skill.row_conn()

    row = conn.execute(
        "SELECT * FROM contacts WHERE email = ?", (email,)
    ).fetchone()
    if not row:
        conn.close()
        return None

    result = dict(row)
    result['phones'] = [
        dict(r) for r in conn.execute(
            "SELECT id, label, number FROM contact_phones WHERE contact_id = ?",
            (result['id'],)
        ).fetchall()
    ]
    result['platforms'] = [
        dict(r) for r in conn.execute(
            "SELECT id, platform, platform_id, label FROM contact_platforms WHERE contact_id = ?",
            (result['id'],)
        ).fetchall()
    ]
    conn.close()
    return result


def find(query):
    """Fuzzy search by name or email. Returns list (max 20).

    Safe: LIKE value passed as ? placeholder.
    """
    like = f"%{query}%"
    return _skill.query_all("""
        SELECT id, name, email, circle, role FROM contacts
        WHERE name LIKE ? OR email LIKE ?
        ORDER BY name LIMIT 20
    """, (like, like))


def check_is_super_admin(email):
    """Check if a contact has super-admin role.

    Returns bool. Parameterized query — no injection possible.
    """
    row = _skill.query_one(
        "SELECT role FROM contacts WHERE email = ?", (email,)
    )
    return row is not None and row['role'] == 'super-admin'


def has_permission(email, permission):
    """Check if a contact has a specific permission granted."""
    row = _skill.query_one("""
        SELECT ar.id FROM auth_rules ar
        JOIN contacts c ON c.id = ar.contact_id
        WHERE c.email = ? AND ar.permission = ?
          AND (ar.scope = '*' OR ar.scope = 'self')
    """, (email, permission))
    return row is not None


def get_permissions(email):
    """Get all permissions for a contact. Returns list of {permission, scope}."""
    return _skill.query_all("""
        SELECT ar.permission, ar.scope FROM auth_rules ar
        JOIN contacts c ON c.id = ar.contact_id
        WHERE c.email = ?
    """, (email,))


# ═══════════════════════════════════════════════════════════
# WRITERS
#   Every write function:
#     1. Checks permission (super-admin) FIRST
#     2. Uses a manual connection for multi-statement transactions
#     3. Returns dict — {'success': True, ...} or {'error': '...'}
# ═══════════════════════════════════════════════════════════

def add(name, email, requester_email, circle=None, role='contact',
        phone=None, platforms=None):
    """Add a new contact. Only super-admin can add.

    Args:
        name: Display name
        email: Unique email address
        requester_email: Must belong to a super-admin
        circle: 'family', 'friends', 'work', etc. (default: 'family')
        role: 'contact' or 'super-admin' (default: 'contact')
        phone: Optional phone string
        platforms: Optional list of {'platform', 'id', 'label'}

    Returns:
        {'success': True, 'id': N, 'email': E, 'name': N}
        or {'error': 'Permission denied...'}
    """
    conn = _skill.row_conn()

    if not is_super_admin_local(conn, requester_email):
        conn.close()
        return {
            "error": f"Permission denied. {requester_email} is not super-admin."
        }

    existing = conn.execute(
        "SELECT id FROM contacts WHERE email = ?", (email,)
    ).fetchone()
    if existing:
        conn.close()
        return {"error": f"Contact {email} already exists."}

    conn.execute(
        "INSERT INTO contacts (name, email, circle, role, discretion, metadata) "
        "VALUES (?, ?, ?, ?, 'public', '{}')",
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
                "INSERT OR IGNORE INTO contact_platforms "
                "(contact_id, platform, platform_id, label) VALUES (?, ?, ?, ?)",
                (cid, p['platform'], p['id'], p.get('label', 'primary'))
            )

    if role != 'super-admin':
        for perm in ['email.send', 'email.receive']:
            conn.execute(
                "INSERT OR IGNORE INTO auth_rules "
                "(contact_id, permission, scope) VALUES (?, ?, 'self')",
                (cid, perm)
            )

    conn.commit()
    conn.close()
    return {"success": True, "id": cid, "email": email, "name": name}


def grant(email, permission, scope='*', requester_email=None):
    """Grant a permission to a contact. Only super-admin."""
    conn = _skill.row_conn()

    if not requester_email or not is_super_admin_local(conn, requester_email):
        conn.close()
        return {"error": "Permission denied."}

    cid_row = conn.execute(
        "SELECT id FROM contacts WHERE email = ?", (email,)
    ).fetchone()
    if not cid_row:
        conn.close()
        return {"error": f"Contact {email} not found."}

    conn.execute(
        "INSERT OR IGNORE INTO auth_rules "
        "(contact_id, permission, scope) VALUES (?, ?, ?)",
        (cid_row[0], permission, scope)
    )
    conn.commit()
    conn.close()
    return {"success": True, "email": email, "permission": permission}


def update(email, requester_email, **kwargs):
    """Update contact fields. Only super-admin.

    Security:
        Uses safe_update() from elko_util — columns validated against
        whitelist, values passed as ? placeholders, updated_at auto-appended.
    """
    conn = _skill.row_conn()

    if not is_super_admin_local(conn, requester_email):
        conn.close()
        return {
            "error": "Permission denied. Only super-admin can update contacts."
        }

    updates = dict(kwargs)
    if 'metadata' in updates and isinstance(updates['metadata'], dict):
        updates['metadata'] = json.dumps(updates['metadata'])

    try:
        sql, params = safe_update(
            'contacts', updates, 'email = ?', [email], _CONTACT_COLUMNS
        )
    except ValueError as e:
        conn.close()
        return {"error": str(e)}

    conn.execute(sql, params)
    conn.commit()
    conn.close()

    updated = [k for k in kwargs if k in _CONTACT_COLUMNS]
    return {"success": True, "updated": updated}


# ═══════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════

def is_super_admin_local(conn, email):
    """Local alias for elko_util.is_super_admin.

    Keeps write-function code clean while using the shared utility.
    """
    from elko_util import is_super_admin as _check
    return _check(conn, email)


# ═══════════════════════════════════════════════════════════
# UTILITY
# ═══════════════════════════════════════════════════════════

def summary():
    """One-liner for the bootstrap card. Example output::

        12 contacts (1 admin, 5 family)
    """
    conn = _skill.connect()
    total = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
    admins = conn.execute(
        "SELECT COUNT(*) FROM contacts WHERE role = ?", ('super-admin',)
    ).fetchone()[0]
    family = conn.execute(
        "SELECT COUNT(*) FROM contacts WHERE circle = ?", ('family',)
    ).fetchone()[0]
    conn.close()
    return f"{total} contacts ({admins} admin, {family} family)"
