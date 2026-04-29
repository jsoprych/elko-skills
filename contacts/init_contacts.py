#!/usr/bin/env python3
"""
elko-hs-contacts — Initializer (Elko-Skill)
First-run setup. Creates the DB from schema.sql if it doesn't exist.
Offers to add a super-admin on first run (required for the system to function).

Usage:
    python3 init_contacts.py                # Interactive
    python3 init_contacts.py --auto         # Non-interactive (create DB only)
    python3 init_contacts.py --db /path/to/contacts.db
"""
import sqlite3, os, sys, textwrap

DEFAULT_DB = os.environ.get('ELKO_CONTACTS_DB', 'contacts.db')
SCHEMA = os.path.join(os.path.dirname(__file__), 'schema.sql')

def init(db_path, interactive=True):
    db_path = os.path.abspath(db_path)
    
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        conn.close()
        print(f"Contacts DB already exists at {db_path}")
        print(f"  Tables: {[t[0] for t in tables]}")
        return True
    
    print(f"Creating contacts DB at {db_path}...")
    conn = sqlite3.connect(db_path)
    
    if os.path.exists(SCHEMA):
        conn.executescript(open(SCHEMA).read())
        print(f"  Schema loaded from {SCHEMA}")
    else:
        print(f"  WARNING: schema.sql not found at {SCHEMA}")
        print(f"  DB created but empty — run schema.sql manually.")
        conn.close()
        return False
    
    # Insert default permissions template
    conn.executescript("""
        -- Default: super-admin gets everything
        -- Regular contacts get email.send + email.receive (self)
        -- These are populated when a contact is created.
    """)
    
    conn.commit()
    conn.close()
    
    print(f"  Created tables: contacts, contact_phones, contact_platforms, auth_rules")
    
    if interactive:
        print()
        print("The contacts system needs at least one super-admin to function.")
        resp = input("Add yourself as the first super-admin? [Y/n] ").strip().lower()
        if resp != 'n':
            name = input("Your name: ").strip() or "Admin"
            email = input("Your email: ").strip() or "admin@example.com"
            
            conn = sqlite3.connect(db_path)
            conn.execute("""
                INSERT INTO contacts (name, email, role, circle, discretion)
                VALUES (?, ?, 'super-admin', 'owner', 'public')
            """, (name, email))
            
            # Grant all permissions
            cid = conn.execute("SELECT id FROM contacts WHERE email = ?", (email,)).fetchone()[0]
            for perm in ['system.config', 'services.manage', 'contacts.manage', 'contacts.add',
                         'credentials.read', 'credentials.write', 'threads.manage',
                         'email.send', 'email.receive', 'blog.write', 'cron.manage']:
                conn.execute("INSERT INTO auth_rules (contact_id, permission, scope) VALUES (?, ?, '*')",
                           (cid, perm))
            
            conn.commit()
            conn.close()
            print(f"  Added {name} <{email}> as super-admin with all permissions.")
    
    print("  Done. Set ELKO_CONTACTS_DB env var if not using the default path.")
    return True

if __name__ == "__main__":
    db = DEFAULT_DB
    auto = False
    
    for arg in sys.argv[1:]:
        if arg.startswith('--db='):
            db = arg.split('=', 1)[1]
        elif arg == '--auto':
            auto = True
    
    init(db, interactive=not auto)
