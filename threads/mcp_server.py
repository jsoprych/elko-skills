#!/usr/bin/env python3
"""elko-threads MCP server — exposes threads skill as MCP tools via stdio."""
import re
import sys
import os
from pathlib import Path

# Add repo root for elko_util; remove threads/ from path so Python resolves
# `threads` as the namespace package in repo root, not threads.py in this dir.
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_here = os.path.dirname(os.path.abspath(__file__))
sys.path = [_root] + [p for p in sys.path if os.path.normpath(p) != os.path.normpath(_here)]

from fastmcp import FastMCP
from threads import threads

_VERSION = re.search(
    r'^version\s*=\s*"([^"]+)"',
    (Path(__file__).parent / "pyproject.toml").read_text(),
    re.MULTILINE,
).group(1)

mcp = FastMCP(
    "elko-threads",
    version=_VERSION,
    instructions="Cross-channel conversation tracking for AI agents. "
                 "Captures messages from email, Telegram, GitHub, or any channel into persistent threads. "
                 "Call threads_summary first to confirm the skill is active.",
)


# ── READ tools ─────────────────────────────────────────────

@mcp.tool()
def active_threads(limit: int = 10) -> list:
    """List active threads sorted by most recent activity."""
    return threads.active(limit=limit)


@mcp.tool()
def list_threads(status: str = None, limit: int = 20) -> list:
    """List all threads, optionally filtered by status (active, archived, etc.)."""
    return threads.all_by_status(status=status, limit=limit)


@mcp.tool()
def thread_context(topic: str, channel: str = None, limit: int = 50) -> dict:
    """Get full message history for a thread by topic (and optional channel)."""
    return threads.context(topic, channel=channel, limit=limit)


@mcp.tool()
def recent_threads(limit: int = 5) -> list:
    """Most recent activity across all threads."""
    return threads.recent(limit=limit)


@mcp.tool()
def threads_summary() -> str:
    """Quick stats: total threads, active threads, and message count."""
    return threads.summary()


@mcp.tool()
def skill_version() -> str:
    """Returns the elko-threads MCP server version."""
    return _VERSION


# ── WRITE tools ────────────────────────────────────────────

@mcp.tool()
def capture_message(
    topic: str,
    channel: str,
    from_addr: str,
    from_name: str = "",
    subject: str = "",
    body_preview: str = "",
    direction: str = "inbound",
    sent_at: str = None,
    participants: list = None,
) -> dict:
    """Capture a message into a thread. Creates the thread if it doesn't exist.

    channel: email, telegram, github, discord, etc.
    direction: inbound or outbound
    sent_at: ISO8601 timestamp (defaults to now)
    participants: list of email addresses or names
    """
    msg = {
        "from_addr": from_addr,
        "from_name": from_name,
        "subject": subject,
        "body_preview": body_preview,
        "direction": direction,
    }
    if sent_at:
        msg["sent_at"] = sent_at
    return threads.capture(topic, channel, msg, participants=participants)


@mcp.tool()
def tag_thread(topic: str, tag: str) -> dict:
    """Add a tag to a thread (e.g. 'important', 'design', 'follow-up')."""
    return threads.tag(topic, tag)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
