# elko-threads

**Cross-channel conversation tracking for AI agents.**

AI agents lose track of ongoing conversations between sessions. `elko-threads` gives agents a persistent thread store — capturing messages from email, Telegram, GitHub, Discord, or any channel, and exposing them as MCP tools.

## Install

```bash
pip install elko-threads
# or: uvx elko-threads  (zero-install, via uv)
```

## MCP setup (any agent)

```json
{
  "mcpServers": {
    "elko-threads": {
      "command": "uvx",
      "args": ["elko-threads"]
    }
  }
}
```

Or auto-configure all detected platforms:

```bash
python3 install_mcp.py threads
python3 install_mcp.py threads --sandbox   # isolated DB, easy purge
```

## Tools

| Tool | Description |
|------|-------------|
| `active_threads(limit)` | Active threads, newest first |
| `list_threads(status, limit)` | All threads, filterable by status |
| `thread_context(topic, channel)` | Full message history for a thread |
| `recent_threads(limit)` | Latest activity across all threads |
| `threads_summary` | `"8 threads (5 active), 34 messages"` |
| `skill_version` | Server version, synced with `pyproject.toml` and git tag |
| `capture_message(topic, channel, from_addr, ...)` | Add a message; creates thread if new |
| `tag_thread(topic, tag)` | Tag a thread (e.g. 'important', 'follow-up') |

## Python API (direct access)

```python
from threads import threads

threads.active()
threads.capture(
    topic='AI-World-Daily',
    channel='email',
    msg={
        'from_addr': 'editor@example.com',
        'from_name': 'Alice',
        'subject': 'Issue #42',
        'body_preview': 'Following up on...',
        'direction': 'inbound',
    },
    participants=['john@elko.ai']
)
threads.context('AI-World-Daily')
threads.tag('AI-World-Daily', 'important')
threads.summary()
```

## Works without elko-contacts

Threads is standalone — participants can be email addresses or plain names. Install `elko-contacts` alongside for richer contact resolution, but it's not required.

## Configuration

```bash
export ELKO_THREADS_DB=/path/to/threads.db   # override DB location
```

Default DB location: `threads/threads.db` (relative to module).

## Schema

- `threads` — id, topic, channel, participants (JSON), summary, tags (JSON), status, message_count, last_activity
- `messages` — id, thread_id, from_addr, from_name, subject, body_preview, body_hash, direction, channel, sent_at

## Security

- All queries use `?` parameterized placeholders
- body_hash (SHA256[:16]) for deduplication, never stores full body
- 29 tests

## Links

- [Full docs](https://github.com/jsoprych/elko-skills/tree/main/threads/docs)
- [Platform setup guides](https://github.com/jsoprych/elko-skills/tree/main/docs/platforms)
- [elko-skills repo](https://github.com/jsoprych/elko-skills)

## License

MIT — elko.ai
