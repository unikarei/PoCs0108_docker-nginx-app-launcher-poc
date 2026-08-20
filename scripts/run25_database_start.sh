#!/usr/bin/env bash                                          # Use bash to run this script.
set -euo pipefail                                            # Stop on error, undefined variable, or pipe failure.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"                   # Project root is the parent folder of scripts.
cd "$ROOT"                                                   # Move to the project root.

echo "=========================================================" # Print title separator.
echo "[run25] Start external YouTube database"                  # Print script purpose.
echo "=========================================================" # Print title separator.

if ! docker network inspect youtube_transcripter_net >/dev/null 2>&1; then # Require the stable shared network.
  docker network create youtube_transcripter_net >/dev/null                   # Create the network when absent.
fi

docker compose -f database/docker-compose.yml up -d           # Start only the database and preserve its volume.
echo "[OK] External database is running."                       # Show success message.
