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
    - DB path resolved in priority order:
        1. ELKO_{NAME}_DB env var        — explicit override, always wins
        2. Profile path (profiles.json)  — dev/test/prod isolation
        3. ELKO_DATA_DIR/{name}.db       — shared data dir (Docker volume, custom mount)
        4. ~/.local/share/elko/{name}.db — XDG-compliant host default
        5. ./{name}/{name}.db            — dev/repo layout (last resort)
    - Connection: auto-creates parent dirs + DB + schema. Idempotent.
    - SQL injection: safe_update() validates column whitelist, uses ? placeholders.
    - Version tracking: each DB has a meta table with version and installation_id.
    - Profile support: dev/test/prod isolation via profiles.json.
"""
import os, json, sqlite3


# ═══════════════════════════════════════════════════════════
# VERSION
# ═══════════════════════════════════════════════════════════

VERSION = "0.1.0"
"""Current elko-skills framework version. Updated on every release.

The version is stored in each skill's meta table at DB creation time.
On connect(), if meta.version differs from VERSION, a warning is logged.
"""

VERSION_SQL = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
INSERT OR IGNORE INTO meta (key, value) VALUES ('elko_framework_version', '{v}');
INSERT OR IGNORE INTO meta (key, value) VALUES ('installed_at', datetime('now'));
"""


# ═══════════════════════════════════════════════════════════
# PROFILE LOADER
# ═══════════════════════════════════════════════════════════

def _elko_skill_dir():
    """Resolve the elko-skills root directory. Checks env var, then defaults."""
    env_dir = os.environ.get('ELKO_SKILLS_DIR')
    if env_dir:
        return env_dir
    return os.path.dirname(os.path.abspath(__file__))


def load_profile(profile_name=None):
    """Load a profile from profiles.yaml.

    Args:
        profile_name: Name of the profile to load. If None, checks
                      ELKO_PROFILE env var, then defaults to 'prod'.

    Returns:
        dict with profile config, or empty dict if no profile found.
    """
    name = profile_name or os.environ.get('ELKO_PROFILE', 'prod')
    profiles_path = os.path.join(_elko_skill_dir(), 'profiles.json')

    if not os.path.exists(profiles_path):
        return {'name': name, 'skills': {}}

    with open(profiles_path) as f:
        data = json.load(f) or {}

    profiles = data.get('profiles', {})
    return profiles.get(name, {'name': name, 'skills': {}})


# ═══════════════════════════════════════════════════════════
# ELO-SKILL BASE CLASS
# ═══════════════════════════════════════════════════════════

class ElkoSkill:
    """Base class for every elko-skill. Handles DB lifecycle and connection.

    DB path priority (highest to lowest):
        1. ELKO_{NAME}_DB env var
        2. Profile path from profiles.json
        3. ELKO_DATA_DIR/{filename}
        4. ~/.local/share/elko/{filename}   (XDG-compliant host default)
        5. ./{name}/{filename}              (dev/repo layout)
    """

    def __init__(self, name, env_var, default_db_filename, schema_sql):
        """
        Args:
            name: Skill name, e.g. 'contacts'
            env_var: Env var name, e.g. 'ELKO_CONTACTS_DB'
            default_db_filename: Filename, e.g. 'contacts.db'
            schema_sql: CREATE TABLE statements (IF NOT EXISTS)
        """
        self.name = name
        self.env_var = env_var
        self.schema_sql = schema_sql

        # 1. Explicit env var — always wins
        env_path = os.environ.get(env_var)
        if env_path:
            self.db_path = env_path
            return

        # 2. Profile path
        profile = load_profile()
        skill_cfg = profile.get('skills', {}).get(name, {})
        profile_db = skill_cfg.get('db')
        if profile_db:
            self.db_path = profile_db
            return

        # 3. ELKO_DATA_DIR — shared data directory (Docker volume, custom mount)
        data_dir = os.environ.get('ELKO_DATA_DIR')
        if data_dir:
            self.db_path = os.path.join(data_dir, default_db_filename)
            return

        # 4. XDG-compliant host default (~/.local/share/elko/)
        xdg_base = os.environ.get('XDG_DATA_HOME',
                                   os.path.join(os.path.expanduser('~'), '.local', 'share'))
        self.db_path = os.path.join(xdg_base, 'elko', default_db_filename)

    def connect(self):
        """Get a connection. Auto-creates parent dirs + DB + schema + meta table.

        Idempotent — uses IF NOT EXISTS so schema is safe to re-run.
        Returns an open sqlite3.Connection.
        """
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        db_exists = os.path.exists(self.db_path)
        conn = sqlite3.connect(self.db_path)

        if not db_exists:
            conn.executescript(self.schema_sql)
            # Add version tracking
            conn.executescript(VERSION_SQL.format(v=VERSION))
            conn.commit()
        else:
            # Version check — warn on mismatch
            try:
                row = conn.execute(
                    "SELECT value FROM meta WHERE key = 'elko_framework_version'"
                ).fetchone()
                if row and row[0] != VERSION:
                    print(f"[elko-skills] ⚠ {self.name}: DB version={row[0]}, "
                          f"framework version={VERSION}")
            except sqlite3.OperationalError:
                pass  # meta table doesn't exist (pre-versioning DB)

        return conn

    def row_conn(self):
        """Get a connection with row_factory already set to sqlite3.Row."""
        conn = self.connect()
        conn.row_factory = sqlite3.Row
        return conn

    def query_all(self, sql, params=None):
        """Execute a SELECT and return all rows as dicts.

        Shortcut for read-only queries. Handles row_factory + close.
        """
        conn = self.row_conn()
        rows = conn.execute(sql, params or ()).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def query_one(self, sql, params=None):
        """Execute a SELECT and return one row as dict or None.

        Shortcut for read-only queries. Handles row_factory + close.
        """
        conn = self.row_conn()
        row = conn.execute(sql, params or ()).fetchone()
        conn.close()
        return dict(row) if row else None

    def version(self):
        """Return the version of this skill's database."""
        try:
            conn = self.connect()
            rows = conn.execute(
                "SELECT key, value FROM meta WHERE key IN "
                "('elko_framework_version', 'installed_at')"
            ).fetchall()
            conn.close()
            return dict(rows)
        except sqlite3.OperationalError:
            return {}

    @classmethod
    def diagnose(cls, skills=None):
        """Print full environment and path diagnostics for all known skills.

        Shows resolved DB paths, file status, directory permissions, and all
        ELKO_* env vars. Useful for debugging installs across different
        ecosystems (Docker, Claude Code, Cursor, Hermes, OpenCode, etc.).

        Args:
            skills: list of (name, env_var, filename) tuples. Defaults to all.
        """
        if skills is None:
            skills = [
                ('contacts',    'ELKO_CONTACTS_DB',    'contacts.db'),
                ('threads',     'ELKO_THREADS_DB',     'threads.db'),
                ('credentials', 'ELKO_CREDENTIALS_DB', 'credentials.db'),
                ('audit',       'ELKO_AUDIT_DB',       'audit.db'),
                ('tasks',       'ELKO_TASKS_DB',       'tasks.db'),
            ]

        lines = ['', '── elko-skills environment ──────────────────────────']

        # Runtime info
        import platform, sys
        lines.append(f'  platform   : {platform.system()} {platform.release()}')
        lines.append(f'  python     : {sys.version.split()[0]}')
        lines.append(f'  framework  : elko-util v{VERSION}')
        lines.append('')

        # ELKO_* env vars
        elko_vars = {k: v for k, v in os.environ.items() if k.startswith('ELKO_')}
        lines.append('  ELKO_* env vars:')
        for k, v in sorted(elko_vars.items()):
            # Mask sensitive values
            display = v if 'KEY' not in k and 'SECRET' not in k and 'PASSWORD' not in k else '***'
            lines.append(f'    {k:<30} = {display}')
        if not elko_vars:
            lines.append('    (none set)')
        lines.append('')

        # Active profile
        active_profile = os.environ.get('ELKO_PROFILE', 'prod')
        profile = load_profile(active_profile)
        lines.append(f'  active profile : {active_profile}')
        lines.append('')

        # Per-skill DB resolution — mirrors __init__ priority chain
        lines.append('  Skill DB paths:')
        for name, env_var, filename in skills:
            path = os.environ.get(env_var)
            source = f'${env_var}'
            if not path:
                profile_db = profile.get('skills', {}).get(name, {}).get('db')
                if profile_db:
                    path = profile_db
                    source = f'profile:{active_profile}'
                else:
                    data_dir = os.environ.get('ELKO_DATA_DIR')
                    if data_dir:
                        path = os.path.join(data_dir, filename)
                        source = '$ELKO_DATA_DIR'
                    else:
                        xdg = os.environ.get('XDG_DATA_HOME',
                                             os.path.join(os.path.expanduser('~'), '.local', 'share'))
                        path = os.path.join(xdg, 'elko', filename)
                        source = 'XDG default'

            exists = os.path.exists(path)
            parent = os.path.dirname(path)
            writable = os.access(parent, os.W_OK) if os.path.exists(parent) else False
            size = f'{os.path.getsize(path):,} bytes' if exists else '—'

            status = '✓' if exists else '✗ not found'
            perm = 'rw' if writable else '✗ not writable'
            lines.append(f'    {name:<14} [{status}] [{perm}]  {size}')
            lines.append(f'    {"":14} {path}')
            lines.append(f'    {"":14} source: {source}')

        lines.append('')
        lines.append('─' * 54)
        lines.append('')

        report = '\n'.join(lines)
        print(report)
        return report


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

    Validates column names against whitelist, uses ? placeholders for values.

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
