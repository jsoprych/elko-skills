-- ============================================================
-- elko-hs-threads — Hard-Skill Threads Schema
-- ============================================================
-- Cross-channel conversation tracking.
-- Tracks who said what, when, and where — regardless of whether
-- it came from email, Telegram, GitHub, or carrier pigeon.
--
-- Threads reference contacts by ID (logical FK, not enforced
-- by SQLite — threads works standalone with just names if
-- the contacts hard-skill isn't installed).
-- ============================================================

CREATE TABLE IF NOT EXISTS threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,                    -- 'AI-World-Daily', 'Blog-Article-1', 'elko-foundry'
    channel TEXT DEFAULT 'email',           -- email, telegram, github-issue, discord
    channel_id TEXT,                        -- message thread ID, chat ID, issue number
    participants TEXT DEFAULT '[]',         -- JSON array: [contact_id, ...] or ["name", ...]
    summary TEXT,                           -- Brief human-readable context
    tags TEXT DEFAULT '[]',                 -- JSON array: ["important", "design", "action-needed"]
    status TEXT DEFAULT 'active',           -- active, dormant, resolved, archived
    message_count INTEGER DEFAULT 0,
    last_activity TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    message_id TEXT,                        -- Email Message-ID or platform-native ID
    in_reply_to TEXT,                       -- References/In-Reply-To for threading
    subject TEXT,
    from_addr TEXT,                         -- Sender email or platform handle
    from_name TEXT,                         -- Sender display name
    to_addr TEXT,
    cc_addr TEXT,
    body_preview TEXT,                      -- First ~500 chars of body
    body_hash TEXT,                         -- SHA256 for dedup
    direction TEXT DEFAULT 'inbound',       -- inbound, outbound
    channel TEXT DEFAULT 'email',           -- email, telegram, github, etc.
    sent_at TEXT,
    ingested_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_threads_topic ON threads(topic);
CREATE INDEX IF NOT EXISTS idx_threads_status ON threads(status);
CREATE INDEX IF NOT EXISTS idx_threads_last_activity ON threads(last_activity);
CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_messages_from ON messages(from_addr);
