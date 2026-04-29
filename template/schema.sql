CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
INSERT INTO meta (key, value) VALUES ('version', '1.0.0');
INSERT INTO meta (key, value) VALUES ('description', 'Replace this with a description of your elko-skill');

-- ── Example data table ─────────────────────────────────────
-- Replace with your actual schema. Patterns:
-- * JSON columns for flexible/unpredictable fields
-- * Separate tables for anything you query in WHERE clauses
-- * TEXT dates (SQLite has no native date type)
-- * Indexes on columns you filter or join on
-- ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    value TEXT,
    metadata TEXT DEFAULT '{}',       -- JSON: flexible, not queried
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_records_name ON records(name);
