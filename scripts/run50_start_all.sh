#!/usr/bin/env bash                                          # Use bash to run this script.
set -euo pipefail                                            # Stop on error, undefined variable, or pipe failure.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"                  # Directory that contains this script.
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"                         # Project root is the parent folder of scripts.
cd "$ROOT"                                                   # Move to the project root.

echo "=========================================================" # Print title separator.
echo "[run50] Start all services"                              # Print script purpose.
echo "=========================================================" # Print title separator.

"$SCRIPT_DIR/run30_docker_init.sh"                           # Check Docker and key files.
"$SCRIPT_DIR/run20_manager_start.sh"                         # Start host-side Manager API.     (Windows)
sleep 3                                                      # Wait a short time for Manager API startup.
"$SCRIPT_DIR/run32_docker_start_detached.sh"                 # Start "Nginx+Launcher+all apps"  (Docker detached mode)
"$SCRIPT_DIR/run35_docker_status.sh"                         # Show Docker service status.

echo                                                         # Print blank line.
echo "[OK] All start commands finished."                     # Show success message.
echo "Launcher: http://localhost:8080/launcher/"             # Show Launcher URL.
echo "Manager : http://127.0.0.1:9000/health"                # Show Manager API health URL.
