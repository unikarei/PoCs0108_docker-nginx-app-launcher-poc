#!/usr/bin/env bash                                          # Use bash to run this script.
set -euo pipefail                                            # Stop on error, undefined variable, or pipe failure.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"                     # Project root is the parent folder of scripts.
cd "$ROOT"                                                   # Move to the project root.

echo "=========================================================" # Print title separator.
echo "[run30] Check Docker and project files"                  # Print script purpose.
echo "=========================================================" # Print title separator.

command -v docker >/dev/null 2>&1 || {                        # Check whether Docker command exists.
  echo "[ERROR] docker command was not found." >&2             # Explain the error.
  exit 1                                                      # Exit with error.
}                                                             # End Docker command check.

docker --version                                             # Print Docker version.
docker compose version                                       # Print Docker Compose version.
docker info >/dev/null                                       # Check whether Docker Engine is running.

if ! docker network inspect youtube_transcripter_net >/dev/null 2>&1; then # Check the shared internal network.
  docker network create youtube_transcripter_net >/dev/null                 # Create it once when absent.
fi

[ -f "docker-compose.yml" ] && echo "[OK] docker-compose.yml exists." || echo "[WARN] docker-compose.yml is missing."             # Check Compose file.
[ -f "nginx/nginx.conf" ] && echo "[OK] nginx/nginx.conf exists." || echo "[WARN] nginx/nginx.conf is missing."                   # Check Nginx config.
[ -f "launcher/Dockerfile" ] && echo "[OK] launcher Dockerfile exists." || echo "[WARN] launcher Dockerfile is missing."           # Check Launcher Dockerfile.
[ -f "apps/app1/Dockerfile" ] && echo "[OK] app1 Dockerfile exists." || echo "[WARN] app1 Dockerfile is missing."                 # Check App1 Dockerfile.
[ -f "apps/app2/Dockerfile" ] && echo "[OK] app2 Dockerfile exists." || echo "[WARN] app2 Dockerfile is missing."                 # Check App2 Dockerfile.
[ -f "apps/app3/Dockerfile" ] && echo "[OK] app3 Dockerfile exists." || echo "[WARN] app3 Dockerfile is missing."                 # Check App3 Dockerfile.
[ -f "apps/app4/Dockerfile" ] && echo "[OK] app4 Dockerfile exists." || echo "[WARN] app4 Dockerfile is missing."                 # Check App4 Dockerfile.
[ -f "manager-api/src/main.py" ] && echo "[OK] manager-api source exists." || echo "[WARN] manager-api source is missing."         # Check Manager API source.

echo                                                          # Print blank line.
echo "[OK] Docker basic check finished."                       # Show success message.
