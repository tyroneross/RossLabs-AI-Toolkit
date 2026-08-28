#!/usr/bin/env bash
# Install Calm Precision into a consumer as a vendored skill.
#
# RossLabs-AI-Toolkit holds the canonical source at skills/calm-precision/.
# Each consumer gets its own copy so it keeps working when installed standalone.
# Canonical always wins: re-running overwrites the vendored copy in full.
#
#   ./scripts/install-calm-precision.sh <target-skills-dir> [--check]
#
# e.g.
#   ./scripts/install-calm-precision.sh ~/dev/git-folder/RossLabs-AI-Toolkit/plugins/ibr/skills
#   ./scripts/install-calm-precision.sh ~/dev/git-folder/groundwork/skills
#   ./scripts/install-calm-precision.sh ~/.claude/skills
#
# --check exits 1 if the target has drifted from canonical, without writing.
# Use it in CI to catch the hand-copy drift this script exists to prevent.

set -euo pipefail

SRC_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$SRC_ROOT/skills/calm-precision"

TARGET="${1:-}"
MODE="${2:-install}"

if [[ -z "$TARGET" ]]; then
  echo "usage: $0 <target-skills-dir> [--check]" >&2
  exit 2
fi
if [[ ! -d "$SRC" ]]; then
  echo "error: canonical source missing at $SRC" >&2
  exit 2
fi
if [[ ! -d "$TARGET" ]]; then
  echo "error: target '$TARGET' is not a directory" >&2
  exit 2
fi

DEST="$TARGET/calm-precision"
VERSION="$(grep -m1 -oE '^# Calm Precision [0-9]+\.[0-9]+\.[0-9]+' "$SRC/SKILL.md" | awk '{print $4}')"

if [[ "$MODE" == "--check" ]]; then
  if [[ ! -d "$DEST" ]]; then
    echo "DRIFT: $DEST does not exist (canonical is $VERSION)" >&2
    exit 1
  fi
  # .vendored-from is a stamp the installer writes, never present in canonical.
  if diff -rq --exclude='.DS_Store' --exclude='.vendored-from' "$SRC" "$DEST" >/dev/null 2>&1; then
    echo "ok: $DEST matches canonical $VERSION"
    exit 0
  fi
  echo "DRIFT: $DEST differs from canonical $VERSION" >&2
  diff -rq --exclude='.DS_Store' --exclude='.vendored-from' "$SRC" "$DEST" >&2 || true
  exit 1
fi

mkdir -p "$DEST"
rsync -a --delete --exclude='.DS_Store' "$SRC/" "$DEST/"

# Stamp provenance so a reader of the vendored copy knows where to edit.
STAMP="$DEST/.vendored-from"
cat > "$STAMP" <<EOF
source: RossLabs-AI-Toolkit/skills/calm-precision
version: $VERSION
installed: $(date -u +%Y-%m-%dT%H:%M:%SZ)
installer: scripts/install-calm-precision.sh

DO NOT EDIT THIS COPY. Edit the canonical source and re-run the installer.
Verify with: scripts/install-calm-precision.sh <this dir's parent> --check
EOF

echo "installed Calm Precision $VERSION -> $DEST"
