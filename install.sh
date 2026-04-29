#!/usr/bin/env bash
# ============================================================
# elko-skill — Universal Installer
# ============================================================
# Installs an elko-skill on any agent platform:
#   Hermes, Claude Code (ACP), Codex CLI, OpenClaw, OpenCode
#
# Supports parallel installs via profiles (dev/test/prod).
#
# Usage:
#   ./install.sh contacts                          # production install
#   ./install.sh contacts --profile dev             # dev install (separate DB + registry name)
#   ./install.sh contacts --suffix test1           # custom suffix (hs-contacts-test1)
#   ./install.sh contacts --from /path/to/source   # install from local checkout
#   curl -sS https://raw.githubusercontent.com/jsoprych/elko-skills/main/install.sh \
#     | bash -s -- contacts
#
# What it does:
#   1. Clones or copies the skill directory
#   2. Runs init_<skill>.py to create the DB + schema
#   3. Prompts for super-admin (contacts only, first run)
#   4. Registers in elko-registry.db (if Hermes)
#   5. Writes/updates profiles.json
#   6. Prints platform-specific integration instructions
# ============================================================

set -euo pipefail

# ═══════════════════════════════════════════════════════════
# PARSE ARGS
# ═══════════════════════════════════════════════════════════

SKILL_NAME=""
REPO_URL="https://github.com/jsoprych/elko-skills.git"
DEST_DIR="${HOME}/.elko-skills"
PROFILE=""
SUFFIX=""
FROM_PATH=""
SHOW_VERSION=""

while [ $# -gt 0 ]; do
    case "$1" in
        --profile) PROFILE="$2"; shift 2 ;;
        --suffix)  SUFFIX="$2"; shift 2 ;;
        --from)    FROM_PATH="$2"; shift 2 ;;
        --version|-v) SHOW_VERSION=1; shift ;;
        -h|--help) SHOW_HELP=1; shift ;;
        -*)
            echo "Unknown option: $1"
            echo "Usage: $0 <skill> [--profile <name>] [--suffix <name>] [--from <path>]"
            exit 1
            ;;
        *)
            SKILL_NAME="$1"
            shift
            ;;
    esac
done

# ── Help ───────────────────────────────────────────────────
if [ -n "${SHOW_HELP:-}" ] || [ -z "$SKILL_NAME" ]; then
    cat <<HELP
elko-skill installer — one command, five platforms, parallel installs.

Usage:
  ./install.sh <skill> [options]

Skills:
  contacts   People database with permissions
  threads    Cross-channel conversation tracking

Options:
  --profile <name>   Install under a profile (dev, test, prod).
                     Each profile has isolated DB and registry name.
                     Set ELKO_PROFILE=<name> to activate.

  --suffix <name>    Custom suffix instead of profile name.
                     E.g. --suffix test1 → hs-contacts-test1

  --from <path>      Install from a local directory (for development).
                     Points source at your working copy.

  --version, -v      Show installed version and exit.

Examples:
  ./install.sh contacts                    # production (default)
  ./install.sh contacts --profile dev      # dev — separate DB, no conflict
  ./install.sh contacts --suffix mytest    # custom suffix
  export ELKO_PROFILE=dev                  # activate dev profile
  python3 -c "from contacts import contacts as hs; hs.list_all()"
  unset ELKO_PROFILE                       # back to production

  # Development workflow:
  ./install.sh contacts --profile dev --from /home/user/code/elko-skills/contacts
  export ELKO_PROFILE=dev
  # Now "import contacts" uses your working copy + dev DB
  # Edit code, test, repeat. Prod is untouched.
  unset ELKO_PROFILE
HELP
    exit 0
fi

# ── Version info ───────────────────────────────────────────
if [ -n "${SHOW_VERSION:-}" ]; then
    VERSION_FILE="$(dirname "$0")/VERSION"
    if [ -f "$VERSION_FILE" ]; then
        cat "$VERSION_FILE"
    else
        echo "elko-skills (local checkout)"
        echo "Run: git describe --tags 2>/dev/null || echo 'no tags'"
    fi
    exit 0
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  elko-skill: $SKILL_NAME"
[ -n "$PROFILE" ] && echo "  Profile:    $PROFILE"
[ -n "$SUFFIX" ]  && echo "  Suffix:     $SUFFIX"
[ -n "$FROM_PATH" ] && echo "  Source:     $FROM_PATH"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Step 1: Get the code ──────────────────────────────────
if [ -n "$FROM_PATH" ]; then
    # Install from local checkout
    SKILL_SOURCE="$FROM_PATH"
    echo "⟐ Using local source: $SKILL_SOURCE"
    if [ ! -d "$SKILL_SOURCE" ]; then
        echo "✗ Source directory not found: $SKILL_SOURCE"
        exit 1
    fi
    # Create destination
    mkdir -p "$DEST_DIR"
    SKILL_DIR="$DEST_DIR/$SKILL_NAME"
    if [ "$SKILL_SOURCE" != "$SKILL_DIR" ]; then
        echo "⟐ Linking $SKILL_SOURCE → $SKILL_DIR"
        ln -sfn "$SKILL_SOURCE" "$SKILL_DIR"
    fi
elif command -v git &>/dev/null; then
    echo "⟐ Cloning from $REPO_URL..."
    if [ -d "$DEST_DIR/.git" ]; then
        (cd "$DEST_DIR" && git pull) || true
    else
        mkdir -p "$(dirname "$DEST_DIR")"
        git clone --depth 1 "$REPO_URL" "$DEST_DIR"
    fi
    SKILL_DIR="$DEST_DIR/$SKILL_NAME"
else
    echo "✗ git not found. Download the repo manually:"
    echo "  $REPO_URL"
    exit 1
fi

if [ ! -d "$SKILL_DIR" ]; then
    echo "✗ Skill '$SKILL_NAME' not found in $DEST_DIR"
    available=$(ls -d "$DEST_DIR"/*/ 2>/dev/null | xargs -I{} basename {} | tr '\n' ' ')
    echo "  Available: $available"
    exit 1
fi

# ── Step 2: Determine install identity ─────────────────────
# Registry name: hs-<skill>[-<suffix>]
# DB suffix:     same logic
REGISTRY_NAME="hs-$SKILL_NAME"
DB_SUFFIX=""
if [ -n "$SUFFIX" ]; then
    REGISTRY_NAME="hs-${SKILL_NAME}-${SUFFIX}"
    DB_SUFFIX=".$SUFFIX"
elif [ -n "$PROFILE" ] && [ "$PROFILE" != "prod" ]; then
    REGISTRY_NAME="hs-${SKILL_NAME}-${PROFILE}"
    DB_SUFFIX=".$PROFILE"
fi

# ── Step 3: Set up DB path ─────────────────────────────────
if [ -n "$FROM_PATH" ]; then
    # For dev installs, put DB next to source
    DB_PATH="${SKILL_SOURCE}/${SKILL_NAME}${DB_SUFFIX}.db"
else
    DB_PATH="${SKILL_DIR}/${SKILL_NAME}${DB_SUFFIX}.db"
fi

# Export so init script picks it up
export ELKO_${SKILL_NAME^^}_DB="$DB_PATH"

# ── Step 4: Run the initializer ────────────────────────────
INIT_SCRIPT="$SKILL_DIR/init_${SKILL_NAME}.py"
if [ -f "$INIT_SCRIPT" ]; then
    echo "⟐ Initializing database at $DB_PATH..."
    python3 "$INIT_SCRIPT" --db "$DB_PATH" --auto || {
        echo "⚠ Initialization failed. Try manually:"
        echo "  python3 $INIT_SCRIPT --db $DB_PATH"
    }
    echo "✓ Database created"
else
    echo "∼ No init script (schema auto-created on first use)"
fi

# ── Step 5: Update profiles.json ───────────────────────────
PROFILES_FILE="$DEST_DIR/profiles.json"
if [ -n "$PROFILE" ]; then
    echo "⟐ Updating profile '$PROFILE' in $PROFILES_FILE..."

    # Build JSON — uses Python to parse/write safely
    python3 -c "
import os, json

profile_name = '$PROFILE'
skill_name = '$SKILL_NAME'
skill_dir = '$SKILL_DIR'
db_path = '$DB_PATH'
registry_name = '$REGISTRY_NAME'

profiles_path = '$PROFILES_FILE'
existing = {}
if os.path.exists(profiles_path):
    with open(profiles_path) as f:
        existing = json.load(f) or {}

profiles = existing.setdefault('profiles', {})
profile_ = profiles.setdefault(profile_name, {})
skills = profile_.setdefault('skills', {})
skills[skill_name] = {
    'source': '$FROM_PATH' if '$FROM_PATH' else skill_dir,
    'db': db_path,
    'registry_name': registry_name,
}

if 'active_profile' not in existing:
    existing['active_profile'] = 'prod'

with open(profiles_path, 'w') as f:
    json.dump(existing, f, indent=2)

print(f'✓ Profile \"{profile_name}\" updated')
" 2>/dev/null || echo "∼ Could not update profiles.json"
fi

# ── Step 6: Register in Hermes registry (if available) ────
HERMES_REGISTRY="${HERMES_DATA_DIR:-/opt/data}/elko-registry.db"
if [ -f "$HERMES_REGISTRY" ]; then
    echo "⟐ Registering as '$REGISTRY_NAME' in elko-registry..."
    python3 -c "
import sqlite3
db = sqlite3.connect('$HERMES_REGISTRY')
try:
    db.execute(\"INSERT INTO services (name, kind, path, capability, active) VALUES (?, ?, ?, ?, 1)\",
        ('$REGISTRY_NAME', 'elko-skill', '$SKILL_DIR',
         '$SKILL_NAME $([ -n \"$SUFFIX\" ] && echo \"($SUFFIX)\" || echo \"\")'))
    db.commit()
    print(f'✓ Registered as $REGISTRY_NAME')
except sqlite3.IntegrityError:
    print(f'∼ Already registered: $REGISTRY_NAME')
db.close()
" 2>/dev/null || echo "∼ Registry registration skipped"
fi

# ── Step 7: Save version info ────────────────────────────────
VERSION_FILE="$SKILL_DIR/VERSION"
if [ ! -f "$VERSION_FILE" ]; then
    # Use profile name as the version identifier for dev installs
    if [ -n "$PROFILE" ]; then
        echo "profile=$PROFILE" > "$VERSION_FILE"
        echo "registry=$REGISTRY_NAME" >> "$VERSION_FILE"
        echo "db=$DB_PATH" >> "$VERSION_FILE"
        echo "installed=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$VERSION_FILE"
    fi
fi

# ── Step 8: Platform detection ────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  $REGISTRY_NAME installed at:"
echo "    $SKILL_DIR"
echo "  Database:"
echo "    $DB_PATH"
[ -n "$PROFILE" ] && echo "  Profile:  $PROFILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Platform-specific setup:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Detect Hermes
if [ -n "${HERMES_CONFIG:-}" ] || [ -n "${HERMES_DATA_DIR:-}" ] || [ -f "$HOME/.hermes/config.yaml" ]; then
    echo ""
    echo "  ◆ Hermes Agent"
    echo "    Import with profile:"
    echo ""
    echo "        export ELKO_PROFILE=${PROFILE:-prod}"
    echo "        from ${SKILL_NAME} import ${SKILL_NAME} as hs"
    echo "        hs.summary()"
    echo ""
    echo "    Or with env var (no profile needed):"
    echo ""
    echo "        export ELKO_${SKILL_NAME^^}_DB=$DB_PATH"
    echo "        from ${SKILL_NAME} import ${SKILL_NAME} as hs"
    echo ""
fi

# Detect Claude Code
if command -v claude &>/dev/null; then
    echo ""
    echo "  ◆ Claude Code"
    echo "    Add to CLAUDE.md:"
    echo ""
    echo "        ## ${REGISTRY_NAME}"
    if [ -n "$PROFILE" ]; then
        echo "        export ELKO_PROFILE=$PROFILE"
    fi
    echo "        python3 ${SKILL_DIR}/${SKILL_NAME}.py"
    echo ""
fi

# Detect Codex CLI
if command -v codex &>/dev/null; then
    echo ""
    echo "  ◆ Codex CLI"
    echo "    Add to .codex/config.yaml:"
    echo ""
    echo "        tools:"
    echo "          - name: ${REGISTRY_NAME}"
    echo "            path: ${SKILL_DIR}"
    [ -n "$PROFILE" ] && echo "            env:"
    [ -n "$PROFILE" ] && echo "              ELKO_PROFILE: ${PROFILE}"
    echo ""
fi

# Detect OpenClaw
if command -v openclaw &>/dev/null; then
    echo ""
    echo "  ◆ OpenClaw"
    echo "    Import with profile:"
    echo ""
    [ -n "$PROFILE" ] && echo "        os.environ['ELKO_PROFILE'] = '${PROFILE}'"
    echo "        import ${SKILL_NAME}"
    echo "        ${SKILL_NAME}.list_all()"
    echo ""
fi

# Detect OpenCode
if command -v opencode &>/dev/null; then
    echo ""
    echo "  ◆ OpenCode"
    echo "    Add to .opencode/skills.yaml:"
    echo ""
    echo "        skills:"
    echo "          - name: ${REGISTRY_NAME}"
    echo "            path: ${SKILL_DIR}"
    [ -n "$PROFILE" ] && echo "            env:"
    [ -n "$PROFILE" ] && echo "              ELKO_PROFILE: ${PROFILE}"
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✓ $REGISTRY_NAME is ready."
echo ""
echo "  Switch between profiles:"
echo "    export ELKO_PROFILE=${PROFILE:-prod}   # activate this"
echo "    unset ELKO_PROFILE                      # back to prod"
echo ""
echo "  Run tests:  cd ${SKILL_DIR} && python3 -m pytest tests/"
echo "  Docs:       cat ${SKILL_DIR}/docs/howto.md"
echo "  Uninstall:  ./uninstall.sh ${REGISTRY_NAME}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
