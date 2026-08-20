#!/usr/bin/env bash                                          # Use bash to run this script.
set -euo pipefail                                            # Stop on error, undefined variable, or pipe failure.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"                   # Project root is the parent folder of scripts.
cd "$ROOT"                                                   # Move to the project root.

echo "=========================================================" # Print title separator.
echo "[run26] Stop external YouTube database"                   # Print script purpose.
echo "=========================================================" # Print title separator.

docker compose -f database/docker-compose.yml stop            # Stop the database without deleting its volume.
echo "[OK] External database stopped; volume was preserved."    # Show preservation message.
