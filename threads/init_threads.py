#!/usr/bin/env python3
"""
elko-hs-threads — Initializer (Elko-Skill)
First-run setup. Creates the DB from schema.sql if it doesn't exist.

Usage:
    python3 init_threads.py                 # Interactive
    python3 init_threads.py --auto          # Non-interactive
    python3 init_threads.py --db /path/to/threads.db
"""
import sqlite3, os, sys

DEFAULT_DB = os.environ.get('ELKO_THREADS_DB', 'threads.db')
SCHEMA = os.path.join(os.path.dirname(__file__), 'schema.sql')

def init(db_path, interactive=True):
    db_path = os.path.abspath(db_path)
    
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        conn.close()
        print(f"Threads DB already exists at {db_path}")
        print(f"  Tables: {[t[0] for t in tables]}")
        return True
    
    print(f"Creating threads DB at {db_path}...")
    conn = sqlite3.connect(db_path)
    
    if os.path.exists(SCHEMA):
        conn.executescript(open(SCHEMA).read())
        print(f"  Schema loaded from {SCHEMA}")
    else:
        print(f"  WARNING: schema.sql not found at {SCHEMA}")
        conn.close()
        return False
    
    conn.commit()
    conn.close()
    
    print(f"  Created tables: threads, messages")
    print(f"  Indexed by: topic, status, last_activity, from_addr")
    print("  Done. Set ELKO_THREADS_DB env var if not using the default path.")
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
