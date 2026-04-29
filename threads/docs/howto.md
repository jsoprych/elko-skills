# hs-threads — Elko-Skill HOWTO

**threads.db** — cross-channel conversation tracking. Captures discussions from email, Telegram, GitHub, or any channel. Threads work standalone — participants can be stored as names or IDs (contacts DB not required).

---

## Database

- **Path:** `/opt/data/elko-skills/threads/threads.db`
- **Env override:** `ELKO_THREADS_DB`
- **Tables:** `threads`, `messages`
- **Schema:** `elko-skills/threads/schema.sql`

## Key functions (threads.py)

### Capture

```python
# Capture an incoming message (creates thread or appends)
capture(
    channel="email",
    subject="Re: AI World Update",
    body="Latest findings on DeepSeek...",
    participants=["john@elko.ai", "pat@example.com"],
    message_id="<abc123@mail.gmail.com>",
    in_reply_to="<prev@mail.gmail.com>",   # links to parent
    tags=["ai", "research"],
)

# Returns {"thread_id": 7, "message_id": 42, "is_new_thread": False}
```

### Retrieve

```python
get_thread(7)                    # Thread + all messages
get_message(42)                  # Single message
search("DeepSeek")               # Full-text across body + subject
list_recent(limit=10)            # Most recent threads
list_by_tag("ai")                # Threads with a specific tag
list_by_participant("pat@ex.com") # Threads involving a person
```

### Tag management

```python
add_tag(7, "urgent")
remove_tag(7, "urgent")
get_tags(7)                      # Returns ["urgent", "research"]
```

### Stats

```python
summary()                        # Total threads, total messages, by channel
```

## Common queries

```sql
-- Thread count by channel
SELECT channel, COUNT(*) FROM threads GROUP BY channel;

-- Messages in the last 7 days
SELECT t.subject, m.body, m.captured_at
FROM messages m
JOIN threads t ON m.thread_id = t.id
WHERE m.captured_at > datetime('now', '-7 days')
ORDER BY m.captured_at DESC;
```

## Tag queries

```sql
-- Threads tagged "urgent"
SELECT t.id, t.subject, t.updated_at
FROM threads t
JOIN thread_tags tt ON t.id = tt.thread_id
WHERE tt.tag = 'urgent'
ORDER BY t.updated_at DESC;

-- All tags with counts
SELECT tt.tag, COUNT(*) as cnt
FROM thread_tags tt
GROUP BY tt.tag
ORDER BY cnt DESC;
```

## Thread lifecycle

1. First message on a subject → new thread created
2. `in_reply_to` header links it to parent → message appended
3. Same subject, new channel → thread matched by subject (fuzzy)
4. Threads auto-update `updated_at` on each new message
5. Tags survive across messages (add/remove at thread level)

## Channel identifiers

| Channel | participant format |
|---|---|
| email | email address |
| Telegram | `@username` or user_id |
| GitHub | `owner/repo` or username |
| General | any string — threads works standalone |
