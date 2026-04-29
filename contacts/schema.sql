-- ============================================================
-- elko-hs-contacts — Hard-Skill Contacts Schema
-- ============================================================
-- Single source of truth for people, their identities,
-- how to reach them, and what they're authorized to do.
-- 
-- JSON columns for flexible extension.
-- Breakout tables (contact_phones, contact_platforms) for
-- anything you'd query relationally.
-- ============================================================

CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    role TEXT DEFAULT 'contact',          -- super-admin, contact
    circle TEXT DEFAULT 'family',         -- owner, family, colleague, subscriber, vendor
    discretion TEXT DEFAULT 'public',     -- public, internal, secret
    metadata TEXT DEFAULT '{}',           -- JSON: extended properties
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS contact_phones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    label TEXT DEFAULT 'mobile',          -- mobile, home, work, other
    number TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS contact_platforms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,                -- telegram, discord, email, x, github, signal
    platform_id TEXT NOT NULL,             -- user ID, handle, address
    label TEXT DEFAULT 'primary',          -- primary, secondary, backup
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(contact_id, platform)
);

CREATE TABLE IF NOT EXISTS auth_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    permission TEXT NOT NULL,              -- system.config, contacts.manage, email.send, etc.
    scope TEXT DEFAULT '*',               -- * (all), self (own data only), or specific identifier
    granted_at TEXT DEFAULT (datetime('now')),
    UNIQUE(contact_id, permission)
);

-- Default permissions for super-admin: all permissions
-- Default permissions for regular contacts: email.send, email.receive (self only)
