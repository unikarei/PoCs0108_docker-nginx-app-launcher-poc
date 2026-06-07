#!/usr/bin/env bash                                          # Use bash to run this script.
set -euo pipefail                                            # Stop on error, undefined variable, or pipe failure.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"                     # Project root is the parent folder of scripts.
cd "$ROOT"                                                   # Move to the project root.

echo "=========================================================" # Print title separator.
echo "[run31] Start Docker services in foreground"             # Print script purpose.
echo "=========================================================" # Print title separator.
echo "Press Ctrl+C to stop foreground logs."                   # Explain foreground behavior.

test -f "docker-compose.yml" || {                             # Require docker-compose.yml.
  echo "[ERROR] docker-compose.yml was not found." >&2         # Explain the error.
  exit 1                                                      # Exit with error.
}                                                             # End Compose file check.

docker compose up --build                                    # Build and start services with foreground logs.
