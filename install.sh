#!/usr/bin/env bash
# ============================================================
# elko-skill — Universal Installer
# ============================================================
# Installs an elko-skill on any agent platform:
#   Hermes, Claude Code (ACP), Codex CLI, OpenClaw, OpenCode
#
# Usage:
#   curl -sS https://raw.githubusercontent.com/jsoprych/elko-skills/main/install.sh | bash -s -- contacts
#   curl -sS https://raw.githubusercontent.com/jsoprych/elko-skills/main/install.sh | bash -s -- threads
#
# Or local:
#   ./install.sh contacts /path/to/elko-skills
#
# What it does:
#   1. Clones or copies the skill directory
#   2. Runs init_<skill>.py to create the DB + schema
#   3. Prompts for super-admin (first contact)
#   4. Registers in elko-registry.db (if Hermes)
#   5. Prints platform-specific integration instructions
# ============================================================

set -euo pipefail

SKILL_NAME="${1:-}"
SKILL_REPO="${2:-https://github.com/jsoprych/elko-skills.git}"
DEST_DIR="${3:-$HOME/.elko-skills}"

# ── Help ───────────────────────────────────────────────────
if [ -z "$SKILL_NAME" ] || [ "$SKILL_NAME" = "-h" ] || [ "$SKILL_NAME" = "--help" ]; then
    cat <<HELP
elko-skill installer — one command, four platforms.

Usage:
  ./install.sh <skill> [repo-url] [dest-dir]

Skills:
  contacts   People database with permissions
  threads    Cross-channel conversation tracking
  credentials  API keys & secrets (coming soon)

Examples:
  ./install.sh contacts
  ./install.sh threads https://github.com/jsoprych/elko-skills.git ~/.skills
  curl -sS https://raw.githubusercontent.com/jsoprych/elko-skills/main/install.sh \\
    | bash -s -- contacts

Platform detection:
  This script auto-detects which agent framework is running
  and prints the right setup steps for that platform.

  Supported: Hermes, Claude Code, Codex CLI, OpenClaw, OpenCode
HELP
    exit 0
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  elko-skill: $SKILL_NAME"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Step 1: Get the code ──────────────────────────────────
SKILL_DIR="$DEST_DIR/$SKILL_NAME"

if [ -d "$SKILL_DIR" ]; then
    echo "✓ Skill already exists at $SKILL_DIR"
elif command -v git &>/dev/null; then
    echo "⟐ Cloning from $SKILL_REPO..."
    git clone --depth 1 "$SKILL_REPO" "$DEST_DIR" 2>/dev/null || \
        (cd "$DEST_DIR" && git pull)
    SKILL_DIR="$DEST_DIR/$SKILL_NAME"
else
    echo "✗ git not found. Download the repo manually:"
    echo "  $SKILL_REPO"
    exit 1
fi

if [ ! -d "$SKILL_DIR" ]; then
    echo "✗ Skill '$SKILL_NAME' not found in $DEST_DIR"
    echo "  Available: $(ls "$DEST_DIR"/*/init_*.py 2>/dev/null | xargs -I{} basename {} | sed 's/init_//;s/.py//' | tr '\n' ' ')"
    exit 1
fi

# ── Step 2: Run the initializer ────────────────────────────
INIT_SCRIPT="$SKILL_DIR/init_${SKILL_NAME}.py"
if [ -f "$INIT_SCRIPT" ]; then
    echo "⟐ Initializing database..."
    python3 "$INIT_SCRIPT" || {
        echo "✗ Initialization failed. Try manually:"
        echo "  python3 $INIT_SCRIPT"
        exit 1
    }
    echo "✓ Database created"
else
    echo "∼ No init script found (expected: $INIT_SCRIPT)"
    echo "  Schema will be auto-created on first use."
fi

# ── Step 3: Register in Hermes (if available) ─────────────
HERMES_REGISTRY="${HERMES_DATA_DIR:-/opt/data}/elko-registry.db"
if [ -f "$HERMES_REGISTRY" ]; then
    echo "⟐ Registering in elko-registry..."
    python3 -c "
import sqlite3, os
db = sqlite3.connect('$HERMES_REGISTRY')
try:
    db.execute('INSERT INTO services (name, kind, path, capability, active) VALUES (?, ?, ?, ?, 1)',
        ('hs-$SKILL_NAME', 'elko-skill', '$SKILL_DIR',
         'auto-registered by install.sh'))
    db.commit()
    print('✓ Registered as hs-$SKILL_NAME')
except Exception as e:
    print(f'∼ Already registered or error: {e}')
db.close()
" 2>/dev/null || echo "∼ Registry registration skipped"
fi

# ── Step 4: Platform detection ─────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  $SKILL_NAME installed at:"
echo "    $SKILL_DIR"
echo ""
echo "  Platform-specific setup:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Detect Hermes
if [ -n "${HERMES_CONFIG:-}" ] || [ -n "${HERMES_DATA_DIR:-}" ] || [ -f "$HOME/.hermes/config.yaml" ]; then
    echo ""
    echo "  ◆ Hermes Agent"
    echo "    Already registered in elko-registry. Import in your Python code:"
    echo ""
    echo "        from elko_${SKILL_NAME} import ${SKILL_NAME} as hs"
    echo "        hs.summary()"
    echo ""
fi

# Detect Claude Code / ACP
if command -v claude &>/dev/null; then
    echo ""
    echo "  ◆ Claude Code"
    echo "    Add to your CLAUDE.md (project-level skill):"
    echo ""
    echo "        ## elko-skill: $SKILL_NAME"
    echo "        python3 $SKILL_DIR/contacts.py --help"
    echo ""
    echo "    Or use the ACP bridge:"
    echo ""
    echo "        claude --acp --stdio --skill $SKILL_DIR"
    echo ""
fi

# Detect Codex CLI
if command -v codex &>/dev/null; then
    echo ""
    echo "  ◆ Codex CLI"
    echo "    Add to your .codex/config.yaml:"
    echo ""
    echo "        tools:"
    echo "          - name: $SKILL_NAME"
    echo "            path: $SKILL_DIR"
    echo ""
fi

# Detect OpenClaw
if command -v openclaw &>/dev/null; then
    echo ""
    echo "  ◆ OpenClaw"
    echo "    Import in your Claw scripts:"
    echo ""
    echo "        import hs_$SKILL_NAME"
    echo "        hs_$SKILL_NAME.list_all()"
    echo ""
fi

# Detect OpenCode
if command -v opencode &>/dev/null; then
    echo ""
    echo "  ◆ OpenCode"
    echo "    Add to your .opencode/skills.yaml:"
    echo ""
    echo "        skills:"
    echo "          - name: $SKILL_NAME"
    echo "            path: $SKILL_DIR"
    echo ""
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✓ $SKILL_NAME is ready."
echo "  Run tests:  cd $SKILL_DIR && python3 -m pytest tests/"
echo "  Docs:       cat $SKILL_DIR/docs/howto.md"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
