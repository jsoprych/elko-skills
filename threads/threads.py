#!/usr/bin/env python3
"""
elko-hs-threads — Elko-Skill Module
Cross-channel conversation tracking. Captures discussions from email, Telegram,
GitHub, or any channel. Threads work standalone without a contacts module —
participants can be stored as names or IDs.

Relies on elko_util.ElkoSkill for DB lifecycle.

Usage:
    from elko_hs_threads import threads
    threads.active()                        → [{topic, participants, last_activity}]
    threads.capture(topic, channel, msg)    → auto-create or update thread
    threads.context(topic)                  → full message history for a thread
"""
import sqlite3, json, os, hashlib, datetime

from elko_util import ElkoSkill, safe_update

# ── Schema (inline — single source of truth) ───────────────
SCHEMA = """\
CREATE TABLE IF NOT EXISTS threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    channel TEXT DEFAULT 'email',
    channel_id TEXT,
    participants TEXT DEFAULT '[]',
    summary TEXT,
    tags TEXT DEFAULT '[]',
    status TEXT DEFAULT 'active',
    message_count INTEGER DEFAULT 0,
    last_activity TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER REFERENCES threads(id),
    from_addr TEXT, from_name TEXT, subject TEXT,
    body_preview TEXT, body_hash TEXT,
    direction TEXT DEFAULT 'inbound',
    channel TEXT DEFAULT 'email',
    sent_at TEXT,
    ingested_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_topic ON threads(topic);
"""

# ── Skill singleton ────────────────────────────────────────
_skill = ElkoSkill(
    name='threads',
    env_var='ELKO_THREADS_DB',
    default_db_filename='threads.db',
    schema_sql=SCHEMA,
)

_THREAD_COLUMNS = {'topic', 'channel', 'channel_id', 'participants', 'summary', 'tags', 'status'}


def _connect():
    return _skill.connect()


# ═══════════════════════════════════════════════════════════
# READERS
# ═══════════════════════════════════════════════════════════

def active(limit=10):
    """Return active threads sorted by last activity."""
    return _skill.query_all("""
        SELECT id, topic, channel, participants, summary, status, message_count,
               COALESCE(last_activity, created_at) as last
        FROM threads WHERE status = 'active'
        ORDER BY last DESC LIMIT ?
    """, (limit,))


def all_by_status(status=None, limit=20):
    """Return threads filtered by status, or all if None."""
    if status:
        return _skill.query_all("""
            SELECT id, topic, channel, participants, summary, status, message_count, last_activity
            FROM threads WHERE status = ? ORDER BY last_activity DESC LIMIT ?
        """, (status, limit))
    return _skill.query_all("""
        SELECT id, topic, channel, participants, summary, status, message_count, last_activity
        FROM threads ORDER BY last_activity DESC LIMIT ?
    """, (limit,))


def context(topic, channel=None, limit=50):
    """
    Get full message history for a thread. Searches by topic.
    Optionally filter by channel.
    """
    conn = _connect()
    conn.row_factory = sqlite3.Row
    
    if channel:
        rows = conn.execute("""
            SELECT m.id, m.from_addr, m.from_name, m.subject, m.body_preview,
                   m.body_hash, m.direction, m.channel, m.sent_at, m.ingested_at
            FROM messages m JOIN threads t ON m.thread_id = t.id
            WHERE t.topic = ? AND t.channel = ?
            ORDER BY m.sent_at DESC LIMIT ?
        """, (topic, channel, limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT m.id, m.from_addr, m.from_name, m.subject, m.body_preview,
                   m.body_hash, m.direction, m.channel, m.sent_at, m.ingested_at
            FROM messages m JOIN threads t ON m.thread_id = t.id
            WHERE t.topic = ?
            ORDER BY m.sent_at DESC LIMIT ?
        """, (topic, limit)).fetchall()
    
    thread = conn.execute(
        "SELECT id, topic, channel, participants, summary, tags, message_count, status FROM threads WHERE topic = ?",
        (topic,)
    ).fetchone()
    
    conn.close()
    
    return {
        "thread": dict(thread) if thread else None,
        "messages": [dict(r) for r in rows]
    }


def recent(limit=5):
    """Most recent thread activity across all threads."""
    conn = _connect()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT t.topic, t.channel, t.participants, t.message_count, m.from_name,
               m.subject, m.sent_at
        FROM threads t
        LEFT JOIN messages m ON m.thread_id = t.id
        ORDER BY t.last_activity DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════
# WRITERS
# ═══════════════════════════════════════════════════════════

def capture(topic, channel, msg, participants=None):
    """
    Capture a message into a thread. Auto-creates or updates the thread.
    
    Args:
        topic: Thread topic (e.g. 'AI-World-Daily', 'Blog-Article-1')
        channel: 'email', 'telegram', 'github', etc.
        msg: dict with keys: from_addr, from_name, subject, body_preview, sent_at, direction
        participants: list of contact IDs or names
    
    Returns: dict with thread_id, message_id, is_new_thread
    
    Safe: all user data passed as ? placeholders.
    """
    conn = _connect()
    
    thread = conn.execute(
        "SELECT id, participants, message_count FROM threads WHERE topic = ? AND channel = ?",
        (topic, channel)
    ).fetchone()
    
    is_new = False
    if thread:
        thread_id = thread[0]
        existing_participants = json.loads(thread[1] or '[]')
        current_count = thread[2]
    else:
        thread_id = None
    
    if not thread_id:
        conn.execute("""
            INSERT INTO threads (topic, channel, participants, summary, message_count, last_activity)
            VALUES (?, ?, ?, ?, 0, datetime('now'))
        """, (topic, channel, json.dumps(participants or []), topic))
        thread_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        is_new = True
        existing_participants = participants or []
        current_count = 0
    
    if participants:
        merged = list(set(existing_participants + participants))
        conn.execute("UPDATE threads SET participants = ? WHERE id = ?",
                    (json.dumps(merged), thread_id))
    
    body = msg.get('body_preview', '') or ''
    body_hash = hashlib.sha256(body.encode()).hexdigest()[:16]
    
    cursor = conn.execute("""
        INSERT INTO messages (thread_id, from_addr, from_name, subject, body_preview,
                              body_hash, direction, channel, sent_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        thread_id,
        msg.get('from_addr', ''),
        msg.get('from_name', ''),
        msg.get('subject', ''),
        body[:500],
        body_hash,
        msg.get('direction', 'inbound'),
        channel,
        msg.get('sent_at', datetime.datetime.now().isoformat())
    ))
    msg_id = cursor.lastrowid
    
    conn.execute("""
        UPDATE threads SET message_count = message_count + 1, updated_at = datetime('now'),
            last_activity = datetime('now')
        WHERE id = ?
    """, (thread_id,))
    
    conn.commit()
    conn.close()
    
    return {
        "thread_id": thread_id,
        "message_id": msg_id,
        "is_new_thread": is_new
    }


def tag(topic, tag):
    """Add a tag to a thread. Tags are JSON arrays: ['important', 'design'].
    
    Safe: topic and tag passed as ? placeholders.
    """
    conn = _connect()
    thread = conn.execute(
        "SELECT id, tags FROM threads WHERE topic = ?", (topic,)
    ).fetchone()
    if not thread:
        conn.close()
        return {"error": f"Thread '{topic}' not found"}
    
    existing = json.loads(thread[1] or '[]')
    if tag not in existing:
        existing.append(tag)
        conn.execute("UPDATE threads SET tags = ?, updated_at = datetime('now') WHERE id = ?",
                    (json.dumps(existing), thread[0]))
    
    conn.commit()
    conn.close()
    return {"success": True, "tags": existing}


# ═══════════════════════════════════════════════════════════
# UTILITY
# ═══════════════════════════════════════════════════════════

def summary():
    """One-liner for bootstrap card."""
    conn = _connect()
    total = conn.execute("SELECT COUNT(*) FROM threads").fetchone()[0]
    active_count = conn.execute("SELECT COUNT(*) FROM threads WHERE status='active'").fetchone()[0]
    msg_count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    conn.close()
    return f"{total} threads ({active_count} active), {msg_count} messages"


if __name__ == "__main__":
    print("=== THREADS ELKO-SKILL TEST ===")
    print(f"Summary: {summary()}")
    print(f"\nActive: {active()}")
