# Release Process

This document describes the manual release workflow for Asset Optimizer.

## Overview

Releases are cut using a single shell script at `scripts/release.sh`. The operator provides the target semver once; the script validates preconditions, updates version surfaces, creates a release commit, publishes an annotated tag, and pushes to origin.

**No CI/CD automation is used for v0.x.** The script is the release lane.

## Version Convention

- **Source of truth**: `apps/web/package.json` version field
- **Mirrored to**: `apps/api/app/main.py` — `app = FastAPI(..., version="X.Y.Z")`
- Both must be kept in sync. Use `scripts/release.sh` for all releases.
- Tags use annotated format: `vX.Y.Z` (e.g. `v0.8.0`)

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| `jq` | 1.7+ | Safe JSON version updates |
| `git` | any | Version control |
| Bash | 4+ | Script interpreter |

Install `jq`:

```bash
# macOS
brew install jq

# Linux (Debian/Ubuntu)
apt install jq

# Linux (Fedora/RHEL)
dnf install jq

# verify
jq --version
```

## Release Flow

### Standard Release

```bash
# 1. Ensure you are on main with a clean tree
git status
git checkout main
git pull origin main

# 2. Run the release script
scripts/release.sh 0.8.0

# 3. Verify the push
git log --oneline -3
git tag -l "v0.8.0"
```

### Dry Run (Validation Only)

```bash
DRY_RUN=1 scripts/release.sh 0.8.0
```

This runs all guards and prints the intended actions but skips git push.

## Rollback

If a release fails mid-script, files are automatically restored. If you need manual rollback after a partial or completed push:

### Undo Local Tag

```bash
git tag -d vX.Y.Z
```

### Remove Remote Tag

```bash
git push origin --delete vX.Y.Z
```

### Revert Commit

```bash
# Find the commit
git log --oneline

# Reset to previous commit (keep changes staged)
git reset --soft HEAD~1

# Or hard reset (destroy the commit)
git reset --hard HEAD~1
```

### Restore Version Files Manually

```bash
# Restore package.json
git checkout HEAD~1 -- apps/web/package.json

# Restore main.py
git checkout HEAD~1 -- apps/api/app/main.py
```

## Versioning Policy

See `CLAUDE.md` → **Versioning Policy** for the full semantic versioning guide.

TL;DR:
- `PATCH` (`0.8.1`) — bug fixes, non-breaking internal improvements
- `MINOR` (`0.9.0`) — new capabilities, backward compatible
- `MAJOR` (`1.0.0`) — breaking changes, stable public baseline

## Release Notes

Use `RELEASE_NOTES_TEMPLATE.md` at the project root for each release. Copy the template, fill in the sections, and commit alongside the version bump.

## Troubleshooting

### "jq is required but not installed"

Install `jq` first. See Prerequisites above.

### "Working tree is not clean"

Commit or stash your current changes before releasing:

```bash
git add -A && git stash   # temporary
# ... run release ...
git stash pop             # restore
```

### "Not on 'main' branch"

Switch to main and pull latest:

```bash
git checkout main && git pull origin main
```

### "Target version X.Y.Z must be greater than current"

You cannot release a version lower than or equal to the current version. Bump to a higher semver.

### "Tag 'vX.Y.Z' already exists"

Choose a new version, or delete the existing tag:

```bash
# Local
git tag -d vX.Y.Z

# Remote (if already pushed)
git push origin --delete vX.Y.Z
```

## Links

- [Versioning Policy](../CLAUDE.md#versioning-policy)
- [Setup & Operations](./setup.md)
- [Environment Reference](./environment.md)