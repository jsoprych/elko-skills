# hs-threads — Elko-Skill HOWTO

**threads.db** — cross-channel conversation tracking. Captures discussions from email, Telegram, GitHub, or any channel. Threads work standalone — participants can be stored as names or IDs (contacts DB not required).

---

## Quick install

```bash
git clone https://github.com/jsoprych/elko-skills.git
cd elko-skills
./install.sh threads
```

See [`docs/platforms/`](../docs/platforms/) for platform-specific setup.

---

## Database

- **Path:** `/opt/data/elko-skills/threads/threads.db` (default)
- **Env override:** `ELKO_THREADS_DB`
- **Tables:** `threads`, `messages`
- **Schema:** `schema.sql`

## Key functions

### Capture

```python
capture(
    channel="email",
    topic="AI-World-Daily",
    msg={
        "from_addr": "john@elko.ai",
        "from_name": "John",
        "subject": "Re: Today's findings",
        "body_preview": "The DeepSeek API pricing changed...",
        "direction": "inbound",
        "sent_at": "2026-04-28T14:00:00Z",
    },
    participants=["john@elko.ai", "pat@example.com"],
)

# Returns {"thread_id": 7, "message_id": 42, "is_new_thread": False}
```

### Retrieve

```python
active(limit=10)                         # Active threads, newest first
context("AI-World-Daily")                # Full thread + messages
context("AI-World-Daily", channel="telegram")  # Filter by channel
recent(limit=5)                          # Most recent activity across all threads
all_by_status("active")                  # Filter by status
```

### Tag management

```python
tag("AI-World-Daily", "important")
tag("AI-World-Daily", "research")
```

Tags are stored as JSON arrays. Adding the same tag twice is idempotent.

### Stats

```python
summary()     # Returns string: "8 threads (5 active), 34 messages"
```

## Common queries

```sql
-- Thread count by channel
SELECT channel, COUNT(*) FROM threads GROUP BY channel;

-- Messages in the last 7 days
SELECT t.topic, m.body_preview, m.sent_at
FROM messages m
JOIN threads t ON m.thread_id = t.id
WHERE m.sent_at > datetime('now', '-7 days')
ORDER BY m.sent_at DESC;

-- All threads tagged "important"
SELECT t.id, t.topic, t.updated_at
FROM threads t
WHERE t.tags LIKE '%"important"%'
ORDER BY t.updated_at DESC;

-- Threads involving a specific participant
SELECT * FROM threads
WHERE participants LIKE '%john@elko.ai%';
```

## Thread lifecycle

1. First message on a `topic` + `channel` → new thread created
2. Same topic + channel → message appended to existing thread
3. Same topic, different channel → separate thread (independent)
4. Participants merge on each capture (deduplicated)
5. `message_count` auto-increments
6. `last_activity` and `updated_at` auto-update

## Testing

```bash
cd elko-skills/threads
python3 -m pytest tests/ -v
```

## Security

- All queries use `?` parameterized placeholders — no SQL injection
- Threads has no permission model (capture-only); if you need write protection, add it at the transport layer
