#!/usr/bin/env bash                                          # Use bash to run this script.
set -euo pipefail                                            # Stop on error, undefined variable, or pipe failure.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"                     # Project root is the parent folder of scripts.
SERVICE="${1:-}"                                             # Optional service name from first argument.
cd "$ROOT"                                                   # Move to the project root.

echo "=========================================================" # Print title separator.
echo "[run34] Show Docker logs"                                # Print script purpose.
echo "=========================================================" # Print title separator.

test -f "docker-compose.yml" || {                             # Require docker-compose.yml.
  echo "[ERROR] docker-compose.yml was not found." >&2         # Explain the error.
  exit 1                                                      # Exit with error.
}                                                             # End Compose file check.

if [ -z "$SERVICE" ]; then                                    # Show all logs when no service is specified.
  docker compose logs -f                                      # Follow logs for all services.
else                                                          # Show one service log when service is specified.
  docker compose logs -f "$SERVICE"                           # Follow logs for one service.
fi                                                            # End service selection.
