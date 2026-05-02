#!/usr/bin/env python3
"""
install_mcp.py — Auto-configure elko-skills MCP servers for AI agent platforms.

Detects installed platforms and injects the MCP server entry into each one's
config file. Supports sandbox mode (isolated DB, zero-footprint, easy purge).

Usage:
    python3 install_mcp.py contacts
    python3 install_mcp.py threads
    python3 install_mcp.py all
    python3 install_mcp.py contacts --sandbox
    python3 install_mcp.py contacts --platform cursor
    python3 install_mcp.py contacts --dry-run
    python3 install_mcp.py contacts --remove
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ── Known skills ───────────────────────────────────────────
SKILLS = ["contacts", "threads"]

# ── Platform registry ──────────────────────────────────────
# Each entry: detection fn → (config_path, config_key, formatter)
# formatter(skill, server_entry) → dict to merge into config file
#
# "standard" platforms use {"mcpServers": {"elko-X": {...}}}
# non-standard ones get printed as snippets only.

PLATFORMS = {}  # populated below


def _home():
    return Path.home()


def _macos():
    return sys.platform == "darwin"


def _linux():
    return sys.platform.startswith("linux")


def _windows():
    return sys.platform == "win32"


# ── Platform definitions ───────────────────────────────────

def _claude_desktop_config_path():
    if _macos():
        return _home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if _linux():
        return _home() / ".config" / "Claude" / "claude_desktop_config.json"
    if _windows():
        appdata = os.environ.get("APPDATA", "")
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    return None


def _detect_claude_desktop():
    p = _claude_desktop_config_path()
    if p and p.parent.exists():
        return True
    # Also match if the binary is in PATH (app may exist but dir not yet created)
    return shutil.which("claude") is not None and not shutil.which("claude").endswith("claude-code")


def _detect_claude_code():
    cl = shutil.which("claude")
    if cl:
        return True
    return (_home() / ".claude").is_dir()


def _detect_cursor():
    return (_home() / ".cursor").is_dir() or shutil.which("cursor") is not None


def _detect_windsurf():
    return (_home() / ".codeium" / "windsurf").is_dir() or shutil.which("windsurf") is not None


def _detect_zed():
    return (_home() / ".config" / "zed").is_dir() or shutil.which("zed") is not None


def _detect_vscode():
    return shutil.which("code") is not None or shutil.which("code-insiders") is not None


# ── Config injectors ───────────────────────────────────────
# Each returns (config_path, top_key) for the "standard" mcpServers format.
# None means "print snippet only".

def _standard_inject(config_path, top_key, skill_name, entry, dry_run):
    """Read-merge-write a JSON config file safely."""
    path = Path(config_path)

    if dry_run:
        print(f"    [dry-run] would write to: {path}")
        print(f"    entry: {json.dumps({skill_name: entry}, indent=6)}")
        return True

    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            print(f"    ⚠  Could not parse {path} — skipping auto-inject")
            return False
    else:
        data = {}

    if top_key not in data:
        data[top_key] = {}
    data[top_key][skill_name] = entry

    path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"    ✓  Updated {path}")
    return True


# ── MCP entry builder ──────────────────────────────────────

def _build_entry(skill, script_path, sandbox_dir=None, use_uvx=False):
    """Build the mcpServers entry dict for a skill."""
    env = {}

    if sandbox_dir:
        db_path = str(Path(sandbox_dir) / f"{skill}.db")
        env[f"ELKO_{skill.upper()}_DB"] = db_path

    if use_uvx:
        command, args = "uvx", [f"elko-{skill}"]
    else:
        command, args = "python3", [str(script_path)]

    entry = {"command": command, "args": args}
    if env:
        entry["env"] = env
    return entry


# ── Per-platform install actions ───────────────────────────

def install_claude_desktop(skill, entry, dry_run):
    p = _claude_desktop_config_path()
    if not p:
        return False
    return _standard_inject(p, "mcpServers", f"elko-{skill}", entry, dry_run)


def install_claude_code(skill, entry, dry_run):
    # Claude Code reads mcpServers from ~/.claude/settings.json
    p = _home() / ".claude" / "settings.json"
    return _standard_inject(p, "mcpServers", f"elko-{skill}", entry, dry_run)


def install_cursor(skill, entry, dry_run):
    # Cursor reads ~/.cursor/mcp.json
    p = _home() / ".cursor" / "mcp.json"
    return _standard_inject(p, "mcpServers", f"elko-{skill}", entry, dry_run)


def install_windsurf(skill, entry, dry_run):
    # Windsurf reads ~/.codeium/windsurf/mcp_config.json
    p = _home() / ".codeium" / "windsurf" / "mcp_config.json"
    return _standard_inject(p, "mcpServers", f"elko-{skill}", entry, dry_run)


def install_zed(skill, entry, dry_run):
    # Zed uses a different key: context_servers
    # Format: {"context_servers": {"elko-contacts": {"command": "uvx", "args": [...]}}}
    p = _home() / ".config" / "zed" / "settings.json"
    zed_entry = {
        "command": entry["command"],
        "args": entry.get("args", []),
    }
    if "env" in entry:
        zed_entry["env"] = entry["env"]
    return _standard_inject(p, "context_servers", f"elko-{skill}", zed_entry, dry_run)


def install_vscode(skill, entry, dry_run):
    # VS Code GitHub Copilot MCP: .vscode/mcp.json in workspace root
    # Since we don't know the workspace, just print the snippet
    return False  # falls through to snippet print


PLATFORM_REGISTRY = {
    "claude-desktop": (_detect_claude_desktop, install_claude_desktop, "Claude Desktop"),
    "claude-code":    (_detect_claude_code,    install_claude_code,    "Claude Code"),
    "cursor":         (_detect_cursor,         install_cursor,         "Cursor"),
    "windsurf":       (_detect_windsurf,       install_windsurf,       "Windsurf"),
    "zed":            (_detect_zed,            install_zed,            "Zed"),
    "vscode":         (_detect_vscode,         install_vscode,         "VS Code (snippet only)"),
}


# ── Snippet printers (for platforms we can't auto-configure) ──

def print_snippet(skill, entry):
    """Print the JSON snippet for manual pasting."""
    snippet = {"mcpServers": {f"elko-{skill}": entry}}
    print(f"""
    Paste into your MCP config file:

{json.dumps(snippet, indent=4)}
""")


def print_vscode_snippet(skill, entry):
    vscode = {"servers": {f"elko-{skill}": {"type": "stdio", **entry}}}
    print(f"""
    VS Code — add to .vscode/mcp.json in your workspace:

{json.dumps(vscode, indent=4)}
""")


def print_opencode_snippet(skill, entry):
    script = entry["args"][0] if not entry["command"] == "uvx" else f"uvx elko-{skill}"
    print(f"""
    OpenCode — add to .opencode/config.json:
      MCP support: coming soon. For now use the Python import path.
      Script: {script}
""")


# ── Sandbox helpers ────────────────────────────────────────

SANDBOX_DIR = _home() / ".elko-sandbox"


def setup_sandbox(skill):
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    db = SANDBOX_DIR / f"{skill}.db"
    env_file = SANDBOX_DIR / "activate.env"

    line = f'export ELKO_{skill.upper()}_DB="{db}"\n'
    existing = env_file.read_text() if env_file.exists() else ""
    key = f"ELKO_{skill.upper()}_DB"
    if key not in existing:
        with env_file.open("a") as f:
            f.write(line)

    print(f"  Sandbox DB:  {db}")
    print(f"  Activate:    source {env_file}")
    print(f"  Purge all:   rm -rf {SANDBOX_DIR}")
    return str(SANDBOX_DIR)


# ── Core install logic ─────────────────────────────────────

def install_skill(skill, args):
    repo_root = Path(__file__).parent
    script_path = repo_root / skill / "mcp_server.py"

    if not script_path.exists():
        print(f"  ✗  No mcp_server.py found for skill '{skill}' at {script_path}")
        return

    sandbox_dir = None
    if args.sandbox:
        print(f"\n── Sandbox setup for elko-{skill} ──────────────────")
        sandbox_dir = setup_sandbox(skill)

    use_uvx = args.uvx and shutil.which("uvx") is not None
    if args.uvx and not use_uvx:
        print("  ⚠  uvx not found in PATH — falling back to python3")

    entry = _build_entry(skill, script_path.resolve(), sandbox_dir, use_uvx)

    # Determine which platforms to target
    if args.platform:
        targets = {args.platform: PLATFORM_REGISTRY[args.platform]}
    else:
        targets = PLATFORM_REGISTRY

    print(f"\n── Installing elko-{skill} MCP server ──────────────")

    installed_any = False
    for platform_id, (detect, installer, label) in targets.items():
        if not detect():
            continue

        print(f"  {label}")
        ok = installer(skill, entry, args.dry_run)
        if not ok:
            # Platform detected but couldn't auto-configure — print snippet
            if platform_id == "vscode":
                print_vscode_snippet(skill, entry)
            else:
                print_snippet(skill, entry)
        installed_any = True

    if not installed_any:
        print("  No supported platforms detected.")
        print("  Use one of these snippets to configure manually:")
        print_snippet(skill, entry)

    if not args.dry_run and not args.sandbox:
        print(f"\n  Test it now:")
        print(f"    python3 {script_path}")


def remove_skill(skill, args):
    """Remove elko-{skill} entry from all detected platform configs."""
    targets = {args.platform: PLATFORM_REGISTRY[args.platform]} if args.platform else PLATFORM_REGISTRY

    print(f"\n── Removing elko-{skill} from platform configs ─────")
    for platform_id, (detect, _, label) in targets.items():
        if platform_id in ("vscode",) or not detect():
            continue

        # We need the config path — replicate the injector logic
        config_map = {
            "claude-desktop": (_claude_desktop_config_path(), "mcpServers"),
            "claude-code":    (_home() / ".claude" / "settings.json", "mcpServers"),
            "cursor":         (_home() / ".cursor" / "mcp.json", "mcpServers"),
            "windsurf":       (_home() / ".codeium" / "windsurf" / "mcp_config.json", "mcpServers"),
            "zed":            (_home() / ".config" / "zed" / "settings.json", "context_servers"),
        }
        if platform_id not in config_map:
            continue

        config_path, top_key = config_map[platform_id]
        if not config_path or not Path(config_path).exists():
            continue

        try:
            data = json.loads(Path(config_path).read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            continue

        key = f"elko-{skill}"
        if top_key in data and key in data[top_key]:
            if not args.dry_run:
                del data[top_key][key]
                Path(config_path).write_text(json.dumps(data, indent=2) + "\n")
            print(f"  ✓  Removed from {label} ({config_path})")
        else:
            print(f"  –  Not found in {label}")


# ── CLI ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Configure elko-skills MCP servers for AI agent platforms."
    )
    parser.add_argument(
        "skill",
        choices=SKILLS + ["all"],
        nargs="?",
        default=None,
        help="Skill to install (or 'all')",
    )
    parser.add_argument(
        "--sandbox",
        action="store_true",
        help=f"Use isolated sandbox DBs in {SANDBOX_DIR}. Easy to purge.",
    )
    parser.add_argument(
        "--platform",
        choices=list(PLATFORM_REGISTRY.keys()),
        metavar="PLATFORM",
        help=f"Target only one platform: {', '.join(PLATFORM_REGISTRY.keys())}",
    )
    parser.add_argument(
        "--uvx",
        action="store_true",
        help="Use 'uvx elko-<skill>' instead of direct python3 path (requires uv + PyPI publish)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without writing any files",
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove elko-<skill> entries from platform configs",
    )
    parser.add_argument(
        "--list-platforms",
        action="store_true",
        help="Show all supported platforms and detection status",
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Show resolved DB paths, permissions, and ELKO_* env vars for this environment",
    )

    args = parser.parse_args()

    if args.list_platforms:
        print("\nPlatform detection status:")
        for pid, (detect, _, label) in PLATFORM_REGISTRY.items():
            status = "✓ detected" if detect() else "– not found"
            print(f"  {label:<22} {status}  ({pid})")
        return

    if args.inspect:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parent))
        from elko_util import ElkoSkill
        ElkoSkill.diagnose()
        return

    if not args.skill:
        parser.print_help()
        return

    skills = SKILLS if args.skill == "all" else [args.skill]

    for skill in skills:
        if args.remove:
            remove_skill(skill, args)
        else:
            install_skill(skill, args)

    print()


if __name__ == "__main__":
    main()
