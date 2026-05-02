#!/usr/bin/env python3
"""elko-contacts CLI — inspect and manage contacts from the terminal."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from contacts import contacts
from elko_util import ElkoSkill


def _print(data):
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2))
    else:
        print(data)


def cmd_list(args):
    _print(contacts.list_all())


def cmd_find(args):
    _print(contacts.find(args.query))


def cmd_get(args):
    result = contacts.get_by_email(args.email)
    _print(result if result else {"error": f"Not found: {args.email}"})


def cmd_add(args):
    _print(contacts.add(
        args.name, args.email,
        requester_email=args.requester,
        circle=args.circle,
        role=args.role,
        phone=args.phone,
    ))


def cmd_update(args):
    kwargs = {k: v for k, v in dict(
        name=args.name,
        circle=args.circle,
        role=args.role,
        discretion=args.discretion,
    ).items() if v is not None}
    _print(contacts.update(args.email, args.requester, **kwargs))


def cmd_grant(args):
    _print(contacts.grant(args.email, args.permission,
                          scope=args.scope, requester_email=args.requester))


def cmd_permissions(args):
    _print(contacts.get_permissions(args.email))


def cmd_is_admin(args):
    result = contacts.check_is_super_admin(args.email)
    print(f"{args.email}: {'super-admin ✓' if result else 'not super-admin'}")


def cmd_summary(args):
    print(contacts.summary())


def cmd_bootstrap(args):
    _print(contacts.bootstrap(args.email))


def cmd_inspect(args):
    ElkoSkill.diagnose()


def main():
    parser = argparse.ArgumentParser(
        prog="elko-contacts",
        description="Manage elko-contacts from the terminal.",
    )
    parser.add_argument(
        "--db", metavar="PATH",
        help="Override DB path (sets ELKO_CONTACTS_DB)",
    )

    sub = parser.add_subparsers(dest="cmd", metavar="COMMAND")
    sub.required = True

    # list
    sub.add_parser("list", help="List all contacts")

    # find
    p = sub.add_parser("find", help="Search contacts by name or email")
    p.add_argument("query")

    # get
    p = sub.add_parser("get", help="Get a contact by email")
    p.add_argument("email")

    # add
    p = sub.add_parser("add", help="Add a contact (requires super-admin)")
    p.add_argument("name")
    p.add_argument("email")
    p.add_argument("--requester", required=True, metavar="EMAIL")
    p.add_argument("--circle", default="family")
    p.add_argument("--role", default="contact")
    p.add_argument("--phone")

    # update
    p = sub.add_parser("update", help="Update a contact (requires super-admin)")
    p.add_argument("email")
    p.add_argument("--requester", required=True, metavar="EMAIL")
    p.add_argument("--name")
    p.add_argument("--circle")
    p.add_argument("--role")
    p.add_argument("--discretion")

    # grant
    p = sub.add_parser("grant", help="Grant a permission (requires super-admin)")
    p.add_argument("email")
    p.add_argument("permission")
    p.add_argument("--requester", required=True, metavar="EMAIL")
    p.add_argument("--scope", default="*")

    # permissions
    p = sub.add_parser("permissions", help="Show permissions for a contact")
    p.add_argument("email")

    # is-admin
    p = sub.add_parser("is-admin", help="Check if a contact is super-admin")
    p.add_argument("email")

    # summary
    sub.add_parser("summary", help="Quick stats")

    # bootstrap
    p = sub.add_parser("bootstrap", help="Seed first super-admin (safe if already exists)")
    p.add_argument("email")

    # inspect
    sub.add_parser("inspect", help="Show resolved DB paths and environment")

    args = parser.parse_args()

    if args.db:
        os.environ["ELKO_CONTACTS_DB"] = args.db

    cmds = {
        "list":        cmd_list,
        "find":        cmd_find,
        "get":         cmd_get,
        "add":         cmd_add,
        "update":      cmd_update,
        "grant":       cmd_grant,
        "permissions": cmd_permissions,
        "is-admin":    cmd_is_admin,
        "summary":     cmd_summary,
        "bootstrap":   cmd_bootstrap,
        "inspect":     cmd_inspect,
    }
    cmds[args.cmd](args)


if __name__ == "__main__":
    main()
