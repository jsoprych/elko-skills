#!/usr/bin/env python3
"""elko-<name> MCP server — starter kit. Replace <name> and add your tools."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastmcp import FastMCP
from template import module  # rename: from <skill> import <module>

mcp = FastMCP(
    "elko-template",  # rename: "elko-<skill-name>"
    instructions="One sentence describing what this skill does for agents.",
)


# ── READ tools (no auth needed) ────────────────────────────

@mcp.tool()
def list_all(limit: int = 50) -> list:
    """List all records."""
    return module.list_all(limit=limit)


@mcp.tool()
def search(query: str) -> list:
    """Search records by name (partial match)."""
    return module.search(query)


@mcp.tool()
def get(id: int) -> dict:
    """Get a single record by ID."""
    result = module.get(id)
    return result if result is not None else {"error": f"Record {id} not found."}


@mcp.tool()
def summary() -> dict:
    """Quick stats about this skill."""
    return module.summary()


# ── WRITE tools (add permission checks as needed) ──────────

@mcp.tool()
def add(name: str, value: str, requester_email: str) -> dict:
    """Add a new record. requester_email must belong to a super-admin."""
    return module.add(name, value, requester_email)


@mcp.tool()
def update_record(id: int, requester_email: str, name: str = None, value: str = None) -> dict:
    """Update a record. requester_email must belong to a super-admin."""
    kwargs = {k: v for k, v in dict(name=name, value=value).items() if v is not None}
    return module.update_record(id, requester_email, **kwargs)


@mcp.tool()
def delete(id: int, requester_email: str) -> dict:
    """Delete a record. requester_email must belong to a super-admin."""
    return module.delete(id, requester_email)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
