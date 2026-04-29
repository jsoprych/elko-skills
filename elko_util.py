"""
elko_util.py — Shared foundation for every elko-skill.

Every elko-skill imports from here instead of rolling its own connection
management, SQL safety, or permission checking. One place to audit for
security. One place to fix for the whole ecosystem.

Import:
    from elko_util import ElkoSkill, safe_update

    skill = ElkoSkill('contacts', env_var='ELKO_CONTACTS_DB', schema=SCHEMA)
    conn = skill.connect()
    conn.execute("SELECT * FROM contacts WHERE email = ?", (email,))

Design:
    - DB path: env var > default path. Env var is ALWAYS authoritative.
    - Connection: auto-creates DB + schema if missing. Idempotent.
    - SQL injection: safe_update() validates column whitelist, uses ? placeholders.
    - Schema: inline string in the skill module, not a separate file.
"""
import os, json, sqlite3


# ═══════════════════════════════════════════════════════════
# ELO-SKILL BASE CLASS
# ═══════════════════════════════════════════════════════════

class ElkoSkill:
    """Base class for every elko-skill. Handles DB lifecycle and connection."""
    
    def __init__(self, name, env_var, default_db_filename, schema_sql):
        """
        Args:
            name: Human-readable skill name (for error messages)
            env_var: env var name like 'ELKO_CONTACTS_DB'
            default_db_filename: 'contacts.db' — used if env var unset
            schema_sql: string of CREATE TABLE statements (with IF NOT EXISTS)
        """
        self.name = name
        self.env_var = env_var
        self.schema_sql = schema_sql
        
        # Resolve DB path — env var always wins
        skill_dir = os.path.dirname(os.path.abspath(__file__))
        self._default_path = os.path.join(skill_dir, name, default_db_filename)
        
        # Allow env var to point anywhere
        env_path = os.environ.get(env_var)
        self.db_path = env_path if env_path else self._default_path
    
    def connect(self):
        """Get a connection. Auto-creates DB + schema on first call.
        
        Idempotent — uses IF NOT EXISTS so schema is safe to re-run.
        """
        db_exists = os.path.exists(self.db_path)
        conn = sqlite3.connect(self.db_path)
        
        if not db_exists:
            conn.executescript(self.schema_sql)
            conn.commit()
        
        return conn
    
    def row_conn(self):
        """Get a connection with row_factory already set to sqlite3.Row."""
        conn = self.connect()
        conn.row_factory = sqlite3.Row
        return conn
    
    def query_all(self, sql, params=None):
        """Execute a SELECT and return all rows as dicts.
        
        Shortcut for read-only queries. Closes the connection.
        """
        conn = self.row_conn()
        rows = conn.execute(sql, params or ()).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    
    def query_one(self, sql, params=None):
        """Execute a SELECT and return one row as dict or None.
        
        Shortcut for read-only queries. Closes the connection.
        """
        conn = self.row_conn()
        row = conn.execute(sql, params or ()).fetchone()
        conn.close()
        return dict(row) if row else None


# ═══════════════════════════════════════════════════════════
# SAFE SQL BUILDERS
# ═══════════════════════════════════════════════════════════
# These functions build parameterized SQL statements safely.
# Keys go through a whitelist. Values are always ? placeholders.
# There is NO string interpolation of user data whatsoever.
#
# The column name whitelist is the second line of defence:
#   Line 1: ? placeholders prevent value injection
#   Line 2: whitelist prevents column-name injection
# ═══════════════════════════════════════════════════════════

def safe_update(table, updates, where_clause, where_params, allowed_columns):
    """
    Build a parameterized UPDATE statement.
    
    Args:
        table: Table name (string literal, not user-supplied)
        updates: dict of {column: value} — only keys in allowed_columns are used
        where_clause: "email = ?" or "id = ? AND active = 1"
        where_params: list of values for where_clause placeholders
        allowed_columns: set of column names allowed in SET clause
    
    Returns:
        (sql_string, param_list)
    
    Example:
        sql, params = safe_update(
            'contacts',
            {'name': 'Alice', 'circle': 'friends'},
            'email = ?',
            ['alice@elko.ai'],
            {'name', 'circle', 'role'}
        )
        # sql:    "UPDATE contacts SET name = ?, circle = ?, updated_at = datetime('now') WHERE email = ?"
        # params: ['Alice', 'friends', 'alice@elko.ai']
    
    Raises:
        ValueError if no valid columns in updates
    
    Safe because:
        1. Column names validated against whitelist — arbitrary columns rejected
        2. All values passed as ? placeholders — never string-interpolated
        3. updated_at = datetime('now') appended automatically
    """
    valid = {k: v for k, v in updates.items() if k in allowed_columns}
    if not valid:
        allowed = ', '.join(sorted(allowed_columns))
        raise ValueError(f"No valid columns to update. Allowed: {allowed}")
    
    set_items = [f"{col} = ?" for col in valid]
    params = list(valid.values())
    
    set_items.append("updated_at = datetime('now')")
    params.extend(where_params)
    
    return f"UPDATE {table} SET {', '.join(set_items)} WHERE {where_clause}", params


def safe_insert(table, data, allowed_columns):
    """
    Build a parameterized INSERT statement.
    
    Args:
        table: Table name (string literal)
        data: dict of {column: value}
        allowed_columns: set of allowed column names
    
    Returns:
        (sql_string, param_list)
    """
    valid = {k: v for k, v in data.items() if k in allowed_columns}
    if not valid:
        allowed = ', '.join(sorted(allowed_columns))
        raise ValueError(f"No valid columns to insert. Allowed: {allowed}")
    
    cols = ', '.join(valid)
    placeholders = ', '.join(['?'] * len(valid))
    
    return f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", list(valid.values())


# ═══════════════════════════════════════════════════════════
# CONVENIENCE CHECKERS
# ═══════════════════════════════════════════════════════════

def is_super_admin(conn, email):
    """Check if a contact has the super-admin role.
    
    Args:
        conn: open sqlite3 connection
        email: contact email to check
    
    Returns:
        bool
    
    Safe: parameterized query, no string injection possible.
    """
    row = conn.execute(
        "SELECT role FROM contacts WHERE email = ?", (email,)
    ).fetchone()
    return row is not None and row[0] == 'super-admin'
