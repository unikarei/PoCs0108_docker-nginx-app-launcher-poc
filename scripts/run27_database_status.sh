#!/usr/bin/env bash                                          # Use bash to run this script.
set -euo pipefail                                            # Stop on error, undefined variable, or pipe failure.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"                   # Project root is the parent folder of scripts.
cd "$ROOT"                                                   # Move to the project root.

echo "=========================================================" # Print title separator.
echo "[run27] External YouTube database status"                  # Print script purpose.
echo "=========================================================" # Print title separator.

docker compose -f database/docker-compose.yml ps              # Show database container status.
docker volume ls --format 'table {{.Name}}\t{{.Driver}}' | grep -i 'youtube-transcripter-db-data' || true # Show matching persistent volume.
