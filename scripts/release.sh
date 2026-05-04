#!/usr/bin/env bash
# =============================================================================
# Asset Optimizer — Manual Release Script
# =============================================================================
# Usage: scripts/release.sh <major.minor.patch>
#
# This script cuts a release by:
#   1. Validating pre-conditions (jq, clean tree, main branch, semver)
#   2. Bumping version in apps/web/package.json and apps/api/app/main.py
#   3. Committing and annotated tagging
#   4. Pushing to origin
#
# Prerequisites: jq, git, Bash 4+
# =============================================================================

set -euo pipefail

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# ─── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WEB_PACKAGE="$REPO_ROOT/apps/web/package.json"
API_MAIN="$REPO_ROOT/apps/api/app/main.py"

# ─── Helpers ─────────────────────────────────────────────────────────────────

info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1" >&2; }
die()     { error "$1"; exit 1; }

usage() {
    cat <<EOF
Usage: $(basename "$0") <major.minor.patch>

Cut a manual release of Asset Optimizer.

Prerequisites:
  - jq      (JSON processor for safe version updates)
  - git     (version control)
  - current branch must be 'main'
  - working tree must be clean

Example:
  $(basename "$0") 0.8.0

The script will:
  1. Validate pre-conditions
  2. Bump version in package.json and main.py
  3. Create a release commit
  4. Create an annotated tag
  5. Push to origin

EOF
    exit 0
}

# ─── Guards ───────────────────────────────────────────────────────────────────

check_arguments() {
    if [[ $# -lt 1 ]]; then
        error "No target version supplied."
        usage
    fi

    TARGET_VERSION="$1"

    # Basic semver format guard
    if ! [[ "$TARGET_VERSION" =~ ^[[:digit:]]+\.[[:digit:]]+\.[[:digit:]]+$ ]]; then
        die "Invalid semver '$TARGET_VERSION'. Expected format: X.Y.Z (e.g. 0.8.0)"
    fi
}

check_jq() {
    if ! command -v jq >/dev/null 2>&1; then
        die "jq is required but not installed. See https://jqlang.github.io/jq/"
    fi
    info "jq $(jq --version)"
}

check_clean_tree() {
    if ! git -C "$REPO_ROOT" diff --quiet --ignore-submodules 2>/dev/null; then
        die "Working tree is not clean. Commit or stash changes before releasing."
    fi
    if ! git -C "$REPO_ROOT" diff --cached --quiet 2>/dev/null; then
        die "Index has staged changes. Commit or unstage before releasing."
    fi
    info "Working tree is clean"
}

check_branch() {
    current_branch=$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
    if [[ "$current_branch" != "main" ]]; then
        die "Not on 'main' branch (currently on '$current_branch'). Switch to main before releasing."
    fi
    info "On branch 'main'"
}

check_version_bump() {
    CURRENT_VERSION=$(jq -r '.version' "$WEB_PACKAGE" 2>/dev/null)

    if [[ -z "$CURRENT_VERSION" || "$CURRENT_VERSION" == "null" ]]; then
        die "Could not read version from $WEB_PACKAGE"
    fi

    info "Current version: $CURRENT_VERSION"
    info "Target version:  $TARGET_VERSION"

    # semver comparison: die if target <= current
    if ! printf '%s\n%s\n' "$CURRENT_VERSION" "$TARGET_VERSION" | sort -V -C 2>/dev/null; then
        die "Target version $TARGET_VERSION must be greater than current $CURRENT_VERSION"
    fi

    info "Version bump is valid"
}

check_tag_absent() {
    if git -C "$REPO_ROOT" rev-parse "v$TARGET_VERSION" >/dev/null 2>&1; then
        die "Tag 'v$TARGET_VERSION' already exists. Choose a new version or delete the existing tag."
    fi
    info "Tag v$TARGET_VERSION does not exist"
}

# ─── Version Bump ─────────────────────────────────────────────────────────────

# shellcheck disable=SC2317  # trap is defined outside errexit scope
rollback_on_failure() {
    error "Release failed. Rolling back changes..."
    git -C "$REPO_ROOT" checkout -- "$WEB_PACKAGE" "$API_MAIN" 2>/dev/null || true
    error "Rollback complete. Both files restored to original state."
    exit 1
}

bump_web_package() {
    info "Bumping apps/web/package.json to $TARGET_VERSION"

    # Atomic write: write to temp file then move
    local tmp
    tmp=$(mktemp)
    jq ".version = \"$TARGET_VERSION\"" "$WEB_PACKAGE" > "$tmp"
    mv "$tmp" "$WEB_PACKAGE"

    info "Bumped apps/web/package.json"
}

bump_api_version() {
    info "Bumping apps/api/app/main.py version to $TARGET_VERSION"

    # Find the version= line in the FastAPI constructor and replace it
    # Pattern: version="X.Y.Z" anywhere in the file
    if grep -q "^app = FastAPI.*version=" "$API_MAIN"; then
        sed -i "s/version=\"[^\"]*\"/version=\"$TARGET_VERSION\"/" "$API_MAIN"
    else
        # Fallback: replace any version="X.Y.Z" pattern
        sed -i "s/version=\"[[:digit:]]\.[[:digit:]]\.[[:digit:]]\"/version=\"$TARGET_VERSION\"/" "$API_MAIN"
    fi

    # Verify the replacement happened
    if ! grep -q "version=\"$TARGET_VERSION\"" "$API_MAIN"; then
        die "Failed to update version in $API_MAIN"
    fi

    info "Bumped apps/api/app/main.py"
}

# ─── Commit & Tag ─────────────────────────────────────────────────────────────

create_commit() {
    info "Creating release commit"
    git -C "$REPO_ROOT" add "$WEB_PACKAGE" "$API_MAIN"
    git -C "$REPO_ROOT" commit -m "chore: release v$TARGET_VERSION"
    info "Committed as $(git -C "$REPO_ROOT" log -1 --oneline)"
}

create_tag() {
    info "Creating annotated tag v$TARGET_VERSION"
    git -C "$REPO_ROOT" tag -a "v$TARGET_VERSION" -m "v$TARGET_VERSION: Release"
    info "Tag created: v$TARGET_VERSION"
}

# ─── Push ─────────────────────────────────────────────────────────────────────

push_to_remote() {
    if [[ "${DRY_RUN:-}" == "1" ]]; then
        warn "DRY_RUN=1 — skipping git push"
        return 0
    fi

    info "Pushing main to origin"
    git -C "$REPO_ROOT" push origin main

    info "Pushing tag v$TARGET_VERSION to origin"
    git -C "$REPO_ROOT" push origin "v$TARGET_VERSION"

    info "Push complete"
}

# ─── Main ─────────────────────────────────────────────────────────────────────

main() {
    cd "$REPO_ROOT"

    info "Asset Optimizer Release Script"
    info "================================"
    echo

    check_arguments "$@"
    check_jq
    check_clean_tree
    check_branch
    check_version_bump
    check_tag_absent

    echo
    info "All guards passed — starting release"
    echo

    # Set rollback trap (only active once we start modifying files)
    trap rollback_on_failure ERR

    bump_web_package
    bump_api_version
    create_commit
    create_tag

    # Disable trap — success path
    trap - ERR

    push_to_remote

    echo
    info "================================"
    info "Release v$TARGET_VERSION complete!"
    info "Tag: v$TARGET_VERSION"
    info "Run 'git log --oneline -3' to verify"
    if [[ "${DRY_RUN:-}" == "1" ]]; then
        warn "DRY_RUN=1 — no push was performed"
    fi
}

main "$@"