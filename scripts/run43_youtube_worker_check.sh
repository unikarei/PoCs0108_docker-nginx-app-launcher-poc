#!/usr/bin/env bash
set -euo pipefail                                            # Stop on error, undefined variable, or pipe failure.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"                   # Project root is the parent folder of scripts.
cd "$ROOT"                                                   # Move to the project root.

echo "=========================================================" # Print title separator.
echo "[run43] Check YouTube Celery worker"                       # Print script purpose.
echo "=========================================================" # Print title separator.

for attempt in $(seq 1 30); do                               # Allow up to one minute for startup.
  health="$(curl -fsS --max-time 3 http://localhost:8080/youtube/api-proxy/health/ 2>/dev/null || true)" # Read routed API health.
  if [[ "$health" == *'"status":"healthy"'* && "$health" == *'workers='* ]]; then # Require API and worker health.
    echo "[OK] YouTube API and Celery worker are healthy."          # Show success message.
    exit 0                                                       # Exit successfully.
  fi
  sleep 2                                                        # Allow containers to start.
done

echo "[ERROR] YouTube Celery worker did not become healthy." >&2   # Explain the failure.
echo "        Check: docker compose logs youtube-transcripter-worker" >&2 # Show recovery command.
exit 1                                                           # Exit with error.
