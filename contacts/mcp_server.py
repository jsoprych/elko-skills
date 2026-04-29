#!/usr/bin/env python3
"""elko-contacts MCP server — exposes contacts skill as MCP tools via stdio."""
import sys
import os

# Add repo root for elko_util; remove contacts/ from path so Python resolves
# `contacts` as the namespace package in repo root, not contacts.py in this dir.
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_here = os.path.dirname(os.path.abspath(__file__))
sys.path = [_root] + [p for p in sys.path if os.path.normpath(p) != os.path.normpath(_here)]

from fastmcp import FastMCP
from contacts import contacts

mcp = FastMCP(
    "elko-contacts",
    instructions="Persistent contact list with permissions for AI agents. "
                 "Reads are open; writes require requester_email of a super-admin.",
)


# ── READ tools ─────────────────────────────────────────────

@mcp.tool()
def list_all() -> list:
    """List all contacts."""
    return contacts.list_all()


@mcp.tool()
def find(query: str) -> list:
    """Find contacts by name or email (partial match, max 20 results)."""
    return contacts.find(query)


@mcp.tool()
def get(email: str) -> dict:
    """Get a contact by email, including phones and platform handles."""
    result = contacts.get_by_email(email)
    return result if result is not None else {"error": f"Contact {email} not found."}


@mcp.tool()
def get_permissions(email: str) -> list:
    """Get all permissions granted to a contact."""
    return contacts.get_permissions(email)


@mcp.tool()
def check_is_super_admin(email: str) -> bool:
    """Check whether a contact has super-admin role."""
    return contacts.check_is_super_admin(email)


@mcp.tool()
def summary() -> str:
    """Quick stats: total contacts with admin and family counts."""
    return contacts.summary()


# ── WRITE tools (all require requester_email of a super-admin) ─

@mcp.tool()
def add(
    name: str,
    email: str,
    requester_email: str,
    circle: str = "family",
    role: str = "contact",
    phone: str = None,
) -> dict:
    """Add a new contact. requester_email must belong to a super-admin."""
    return contacts.add(name, email, requester_email, circle=circle, role=role, phone=phone)


@mcp.tool()
def update(
    email: str,
    requester_email: str,
    name: str = None,
    circle: str = None,
    role: str = None,
    discretion: str = None,
) -> dict:
    """Update a contact's fields. requester_email must belong to a super-admin."""
    kwargs = {k: v for k, v in dict(
        name=name, circle=circle, role=role, discretion=discretion
    ).items() if v is not None}
    return contacts.update(email, requester_email, **kwargs)


@mcp.tool()
def grant(
    email: str,
    permission: str,
    requester_email: str,
    scope: str = "*",
) -> dict:
    """Grant a permission to a contact. requester_email must belong to a super-admin."""
    return contacts.grant(email, permission, scope=scope, requester_email=requester_email)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
