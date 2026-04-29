#!/usr/bin/env python3
"""hs-template — Initializer (Elko-Skill)
First-run setup. Creates the DB from schema.sql if it doesn't exist.
Usage:
    python3 init_template.py                # Interactive
    python3 init_template.py --auto         # Non-interactive (create DB only)
    python3 init_template.py --db /path/to/template.db
"""
import sqlite3, os, sys

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('ELKO_TEMPLATE_DB', os.path.join(SKILL_DIR, 'template.db'))
SCHEMA_PATH = os.path.join(SKILL_DIR, 'schema.sql')


def init():
    """Create the DB if it doesn't exist. Idempotent — safe to call multiple times."""
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
    # Parse --db override
    if '--db' in sys.argv:
        idx = sys.argv.index('--db')
        if idx + 1 < len(sys.argv):
            DB_PATH = sys.argv[idx + 1]
    
    # Parse --auto flag
    auto = '--auto' in sys.argv
    
    init()
    
    if not auto:
        print()
        print("Template initialized. Edit module.py with your domain logic,")
        print("then register in the registry:")
        print()
        print("  INSERT INTO services (name, kind, path, capability, summary_query, active)")
        print("  VALUES ('hs-template', 'elko-skill', '/opt/data/elko-skills/template',")
        print("          'description of what this skill does', 'SELECT COUNT(*) FROM records', 1);")
