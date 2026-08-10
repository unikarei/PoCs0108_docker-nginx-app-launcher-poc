#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# Purpose:
#   Compatibility wrapper for dependency synchronization.
#
# What this script does:
#   - Locates run11_uv_sync.sh in the same directory.
#   - Delegates all arguments to that script unchanged.
#   - Provides a stable alternate entry point for older runbooks or team docs
#     that reference run17 instead of run11.
#
# Typical usage:
#   - ./run17_uv_sync.sh
#   - ./run17_uv_sync.sh (same args as ./run11_uv_sync.sh)
# ------------------------------------------------------------------------------
set -euo pipefail
RUN17_SCRIPT_VERSION="v0.1.0"

if [ "$0" != "${BASH_SOURCE[0]}" ]; then
    printf 'Error: run17_uv_sync.sh must be executed directly, not sourced.\n' >&2
    return 1 2>/dev/null || exit 1
fi

ROOT="$(cd "$(dirname "$0")" && pwd)"
TARGET="$ROOT/run11_uv_sync.sh"

cd "$ROOT" || exit 1

if [ ! -f "$TARGET" ]; then
    echo "[Error] Target script not found: $TARGET" >&2
    exit 1
fi

cat <<EOF
========================================
       run17 wrapper - uv sync
========================================
Script version : $RUN17_SCRIPT_VERSION
Delegating to: run11_uv_sync.sh

EOF

bash "$TARGET" "$@"
