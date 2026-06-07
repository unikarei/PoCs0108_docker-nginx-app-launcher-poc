#!/usr/bin/env bash                                          # Use bash to run this script.
set -euo pipefail                                            # Stop on error, undefined variable, or pipe failure.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"                     # Project root is the parent folder of scripts.
PID_FILE="$ROOT/.run/manager-api.pid"                        # PID file for Manager API.
cd "$ROOT"                                                   # Move to the project root.

echo "=========================================================" # Print title separator.
echo "[run21] Stop host-side Manager API"                      # Print script purpose.
echo "=========================================================" # Print title separator.

if [ ! -f "$PID_FILE" ]; then                                 # Check whether PID file exists.
  echo "[WARN] PID file was not found."                        # Explain that process may not be tracked.
  echo "If Manager API is still running, stop it manually."    # Show manual fallback.
  exit 0                                                      # Exit without hard error.
fi                                                            # End PID file check.

PID="$(cat "$PID_FILE")"                                     # Read Manager API PID.
kill "$PID" 2>/dev/null || true                              # Stop process and ignore already-stopped state.
rm -f "$PID_FILE"                                            # Remove stale PID file.

echo "[OK] Manager API was stopped."                          # Show success message.
