#!/usr/bin/env bash                                          # Use bash to run this script.
set -euo pipefail                                            # Stop on error, undefined variable, or pipe failure.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"                  # Directory that contains this script.
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"                         # Project root is the parent folder of scripts.
cd "$ROOT"                                                   # Move to the project root.

echo "=========================================================" # Print title separator.
echo "[run51] Stop all services"                               # Print script purpose.
echo "=========================================================" # Print title separator.

"$SCRIPT_DIR/run33_docker_stop.sh"                            # Stop Docker Compose services.
"$SCRIPT_DIR/run26_database_stop.sh"                          # Stop the database without removing its volume.
"$SCRIPT_DIR/run21_manager_stop.sh"                           # Stop host-side Manager API.

echo                                                          # Print blank line.
echo "[OK] All stop commands finished."                        # Show success message.
