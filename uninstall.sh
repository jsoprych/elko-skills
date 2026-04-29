#!/usr/bin/env bash
# ============================================================
# elko-skill — Clean Uninstaller
# ============================================================
# Removes an elko-skill cleanly: deletes DB, removes profile
# entry, unregisters from Hermes registry, removes source.
#
# Usage:
#   ./uninstall.sh hs-contacts            # remove production contacts
#   ./uninstall.sh hs-contacts-dev         # remove dev profile
#   ./uninstall.sh hs-contacts --keep-db   # uninstall but keep data
#   ./uninstall.sh --profile dev contacts  # remove dev profile entry
#   ./uninstall.sh --all                   # remove EVERYTHING
# ============================================================

set -euo pipefail

show_help() {
    cat <<HELP
elko-skill uninstaller — clean removal.

Usage:
  ./uninstall.sh <registry-name> [options]
  ./uninstall.sh --profile <name> <skill>
  ./uninstall.sh --all

Options:
  --keep-db       Uninstall the module but keep the database
  --profile <n>   Uninstall from a specific profile
  --all           Remove ALL elko-skills data (DANGEROUS)

Examples:
  ./uninstall.sh hs-contacts             # remove prod contacts
  ./uninstall.sh hs-contacts-dev         # remove dev profile
  ./uninstall.sh hs-contacts --keep-db   # uninstall, keep DB
HELP
}

# ── Parse args ─────────────────────────────────────────────
REGISTRY_NAME=""
PROFILE=""
KEEP_DB=""
REMOVE_ALL=""
UNINSTALL_DIR="${HOME}/.elko-skills"

while [ $# -gt 0 ]; do
    case "$1" in
        --profile)  PROFILE="$2"; shift 2 ;;
        --keep-db)  KEEP_DB=1; shift ;;
        --all)      REMOVE_ALL=1; shift ;;
        -h|--help)  show_help; exit 0 ;;
        -*)
            echo "Unknown option: $1"
            exit 1
            ;;
        *)
            REGISTRY_NAME="$1"
            shift
            ;;
    esac
done

# ── Dangerous: --all ───────────────────────────────────────
if [ -n "${REMOVE_ALL:-}" ]; then
    echo "⚠  DANGER: This will remove ALL elko-skills data!"
    echo "   Directory: $UNINSTALL_DIR"
    echo "   Databases, profiles, and registry entries."
    read -rp "   Type 'yes' to confirm: " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Aborted."
        exit 1
    fi

    # Remove databases
    find "$UNINSTALL_DIR" -name "*.db" -exec rm -v {} \;
    # Remove profiles
    rm -f "$UNINSTALL_DIR/profiles.yaml"
    # Remove source
    rm -rf "$UNINSTALL_DIR"

    # Unregister from Hermes
    HERMES_REGISTRY="${HERMES_DATA_DIR:-/opt/data}/elko-registry.db"
    if [ -f "$HERMES_REGISTRY" ]; then
        python3 -c "
import sqlite3
db = sqlite3.connect('$HERMES_REGISTRY')
db.execute(\"DELETE FROM services WHERE kind='elko-skill'\")
db.commit()
db.close()
print('✓ Cleared all elko-skill registry entries')
" 2>/dev/null || true
    fi

    echo "✓ All elko-skills removed."
    exit 0
fi

# ── Derive skill name from registry name ───────────────────
# hs-contacts       → contacts
# hs-contacts-dev   → contacts (profile=dev)
# hs-contacts-test1 → contacts (suffix=test1)
SKILL_NAME=$(echo "$REGISTRY_NAME" | sed 's/^hs-//' | sed 's/-[^-]*$//')
SUFFIX_OR_PROFILE=$(echo "$REGISTRY_NAME" | sed 's/^hs-//' | sed "s/^${SKILL_NAME}-//")

# If --profile was given, use it as the suffix
[ -n "$PROFILE" ] && SUFFIX_OR_PROFILE="$PROFILE"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Uninstalling: $REGISTRY_NAME"
echo "  Skill:        $SKILL_NAME"
[ -n "$SUFFIX_OR_PROFILE" ] && echo "  Profile/Suffix: $SUFFIX_OR_PROFILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Find the skill directory ───────────────────────────────
if [ -d "$UNINSTALL_DIR/$SKILL_NAME" ]; then
    SKILL_DIR="$UNINSTALL_DIR/$SKILL_NAME"
elif [ -d "$UNINSTALL_DIR" ]; then
    SKILL_DIR="$UNINSTALL_DIR"
else
    SKILL_DIR=""
fi

# ── Delete database ────────────────────────────────────────
if [ -z "${KEEP_DB:-}" ]; then
    # Determine DB path from profiles.yaml or naming convention
    DB_PATHS=()
    PROFILES_FILE="$UNINSTALL_DIR/profiles.yaml"
    if [ -f "$PROFILES_FILE" ]; then
        # Extract from profile
        PYTHON_OUT=$(python3 -c "
import yaml, os
with open('$PROFILES_FILE') as f:
    data = yaml.safe_load(f) or {}
profiles = data.get('profiles', {})
suffix = '$SUFFIX_OR_PROFILE'
for pname, pdata in profiles.items():
    skills = pdata.get('skills', {})
    skill_data = skills.get('$SKILL_NAME', {})
    db = skill_data.get('db', '')
    if db and (pname == suffix or suffix == '' or db.endswith(f'.{suffix}.db')):
        print(db)
" 2>/dev/null) || true
        if [ -n "$PYTHON_OUT" ]; then
            DB_PATHS+=("$PYTHON_OUT")
        fi
    fi

    # Also check default paths
    DEFAULT_DB="$UNINSTALL_DIR/$SKILL_NAME/${SKILL_NAME}.db"
    SUFFIXED_DB="$UNINSTALL_DIR/$SKILL_NAME/${SKILL_NAME}.${SUFFIX_OR_PROFILE}.db"
    [ -f "$DEFAULT_DB" ] && DB_PATHS+=("$DEFAULT_DB")
    [ -f "$SUFFIXED_DB" ] && DB_PATHS+=("$SUFFIXED_DB")

    for DB in "${DB_PATHS[@]}"; do
        [ -f "$DB" ] && rm -v "$DB" && echo "  ✓ Removed DB: $DB"
    done
else
    echo "  ∼ Keeping database (--keep-db)"
fi

# ── Update profiles.yaml ───────────────────────────────────
PROFILES_FILE="$UNINSTALL_DIR/profiles.yaml"
if [ -f "$PROFILES_FILE" ]; then
    echo "⟐ Updating profiles.yaml..."
    python3 -c "
import yaml, os

profiles_path = '$PROFILES_FILE'
suffix = '$SUFFIX_OR_PROFILE'
skill_name = '$SKILL_NAME'

with open(profiles_path) as f:
    data = yaml.safe_load(f) or {}

profiles = data.get('profiles', {})
for pname in list(profiles.keys()):
    skills = profiles[pname].get('skills', {})
    if skill_name in skills:
        # Only remove if profile name or suffix matches
        if suffix == '' or pname == suffix or skill_name.endswith(f'-{suffix}'):
            del skills[skill_name]
            if not skills:
                del profiles[pname]

with open(profiles_path, 'w') as f:
    yaml.dump(data, f, default_flow_style=False, sort_keys=False)
print('✓ profiles.yaml updated')
" 2>/dev/null || echo "∼ Could not update profiles.yaml"
fi

# ── Unregister from Hermes ─────────────────────────────────
HERMES_REGISTRY="${HERMES_DATA_DIR:-/opt/data}/elko-registry.db"
if [ -f "$HERMES_REGISTRY" ]; then
    echo "⟐ Unregistering '$REGISTRY_NAME' from elko-registry..."
    python3 -c "
import sqlite3
db = sqlite3.connect('$HERMES_REGISTRY')
cursor = db.execute('DELETE FROM services WHERE name = ?', ('$REGISTRY_NAME',))
db.commit()
count = cursor.rowcount
db.close()
print(f'✓ Removed {count} registry entries')
" 2>/dev/null || echo "∼ Could not unregister"
fi

# ── Remove symlink or source ───────────────────────────────
if [ -L "$SKILL_DIR" ]; then
    rm "$SKILL_DIR" && echo "✓ Removed symlink: $SKILL_DIR"
elif [ -d "$SKILL_DIR" ]; then
    # Only remove if it's in the elko-skills directory (safe guard)
    if echo "$SKILL_DIR" | grep -q "$UNINSTALL_DIR"; then
        rm -rf "$SKILL_DIR"
        echo "✓ Removed directory: $SKILL_DIR"
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✓ $REGISTRY_NAME uninstalled."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
