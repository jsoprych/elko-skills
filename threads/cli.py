#!/usr/bin/env python3
"""elko-threads CLI — inspect and manage threads from the terminal."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from threads import threads
from elko_util import ElkoSkill


def _print(data):
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2))
    else:
        print(data)


def cmd_active(args):
    _print(threads.active(limit=args.limit))


def cmd_list(args):
    _print(threads.all_by_status(status=args.status, limit=args.limit))


def cmd_context(args):
    _print(threads.context(args.topic, channel=args.channel, limit=args.limit))


def cmd_recent(args):
    _print(threads.recent(limit=args.limit))


def cmd_capture(args):
    msg = {
        "from_addr":    args.from_addr,
        "from_name":    args.from_name or "",
        "subject":      args.subject or "",
        "body_preview": args.body or "",
        "direction":    args.direction,
    }
    if args.sent_at:
        msg["sent_at"] = args.sent_at
    participants = args.participants.split(",") if args.participants else None
    _print(threads.capture(args.topic, args.channel, msg, participants=participants))


def cmd_tag(args):
    _print(threads.tag(args.topic, args.tag))


def cmd_summary(args):
    print(threads.summary())


def cmd_inspect(args):
    ElkoSkill.diagnose()


def main():
    parser = argparse.ArgumentParser(
        prog="elko-threads",
        description="Manage elko-threads from the terminal.",
    )
    parser.add_argument(
        "--db", metavar="PATH",
        help="Override DB path (sets ELKO_THREADS_DB)",
    )

    sub = parser.add_subparsers(dest="cmd", metavar="COMMAND")
    sub.required = True

    # active
    p = sub.add_parser("active", help="List active threads")
    p.add_argument("--limit", type=int, default=10)

    # list
    p = sub.add_parser("list", help="List all threads")
    p.add_argument("--status", default=None)
    p.add_argument("--limit", type=int, default=20)

    # context
    p = sub.add_parser("context", help="Full message history for a thread")
    p.add_argument("topic")
    p.add_argument("--channel", default=None)
    p.add_argument("--limit", type=int, default=50)

    # recent
    p = sub.add_parser("recent", help="Most recent activity across all threads")
    p.add_argument("--limit", type=int, default=5)

    # capture
    p = sub.add_parser("capture", help="Add a message to a thread")
    p.add_argument("topic")
    p.add_argument("channel")
    p.add_argument("from_addr")
    p.add_argument("--from-name", dest="from_name")
    p.add_argument("--subject")
    p.add_argument("--body")
    p.add_argument("--direction", default="inbound", choices=["inbound", "outbound"])
    p.add_argument("--sent-at", dest="sent_at")
    p.add_argument("--participants", help="Comma-separated emails/names")

    # tag
    p = sub.add_parser("tag", help="Tag a thread")
    p.add_argument("topic")
    p.add_argument("tag")

    # summary
    sub.add_parser("summary", help="Quick stats")

    # inspect
    sub.add_parser("inspect", help="Show resolved DB paths and environment")

    args = parser.parse_args()

    if args.db:
        os.environ["ELKO_THREADS_DB"] = args.db

    cmds = {
        "active":  cmd_active,
        "list":    cmd_list,
        "context": cmd_context,
        "recent":  cmd_recent,
        "capture": cmd_capture,
        "tag":     cmd_tag,
        "summary": cmd_summary,
        "inspect": cmd_inspect,
    }
    cmds[args.cmd](args)


if __name__ == "__main__":
    main()
