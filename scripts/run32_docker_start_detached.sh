#!/usr/bin/env bash
set -euo pipefail                                            # Stop on error, undefined variable, or pipe failure.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"                     # Project root is the parent folder of scripts.
cd "$ROOT"                                                   # Move to the project root.

SKIP_DATABASE=0                                               # Start database by default for direct invocation.
NO_BUILD=0                                                    # Build images by default for backward compatibility.

print_help() {
  echo "Usage: run32_docker_start_detached.sh [options]"
  echo "  --skip-database  Do not start the external database."
  echo "  --no-build       Start containers using existing images."
}

while (($# > 0)); do
  case "$1" in
    --skip-database) SKIP_DATABASE=1 ;;
    --no-build) NO_BUILD=1 ;;
    --help) print_help; exit 0 ;;
    *) echo "[ERROR] Unknown option: $1" >&2; print_help; exit 2 ;;
  esac
  shift
done

echo "=========================================================" # Print title separator.
echo "[run32] Start Docker services in background"             # Print script purpose.
echo "=========================================================" # Print title separator.

if ((SKIP_DATABASE == 0)); then "$ROOT/scripts/run25_database_start.sh"; else echo "[SKIP] External database start."; fi

test -f "docker-compose.yml" || {                             # Require docker-compose.yml.
  echo "[ERROR] docker-compose.yml was not found." >&2         # Explain the error.
  exit 1                                                      # Exit with error.
}                                                             # End Compose file check.

if ((NO_BUILD == 0)); then
  docker compose -f docker-compose.yml -f generated/docker-compose.apps.yml up --build -d # Build and start services.
else
  docker compose -f docker-compose.yml -f generated/docker-compose.apps.yml up -d # Start services using existing images.
fi
docker compose -f docker-compose.yml -f generated/docker-compose.apps.yml up -d --force-recreate nginx # Refresh Nginx DNS after app recreation.

echo                                                          # Print blank line.
echo "[OK] Docker services were started."                      # Show success message.
echo "Launcher: http://localhost:8080/launcher/"               # Show Launcher URL.
