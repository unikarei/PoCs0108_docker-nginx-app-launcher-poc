#!/usr/bin/env bash                                          # Use bash to run this script.
set -euo pipefail                                            # Stop on error, undefined variable, or pipe failure.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"                     # Project root is the parent folder of scripts.
cd "$ROOT"                                                   # Move to the project root.

echo "=========================================================" # Print title separator.
echo "[run32] Start Docker services in background"             # Print script purpose.
echo "=========================================================" # Print title separator.

"$ROOT/scripts/run25_database_start.sh"                      # Start the separately managed database.

test -f "docker-compose.yml" || {                             # Require docker-compose.yml.
  echo "[ERROR] docker-compose.yml was not found." >&2         # Explain the error.
  exit 1                                                      # Exit with error.
}                                                             # End Compose file check.

docker compose -f docker-compose.yml -f generated/docker-compose.apps.yml up --build -d # Build and start services.
docker compose -f docker-compose.yml -f generated/docker-compose.apps.yml up -d --force-recreate nginx # Refresh Nginx DNS after app recreation.

echo                                                          # Print blank line.
echo "[OK] Docker services were started."                      # Show success message.
echo "Launcher: http://localhost:8080/launcher/"               # Show Launcher URL.
