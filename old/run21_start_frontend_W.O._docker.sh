#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# Purpose:
#   Start the local Next.js frontend without Docker and automatically point it
#   at the backend port selected by run20_start_backend_W.O._docker.sh.
#
# What this script does:
#   - Sets the frontend UI port to 3000 by default.
#   - Allows RUN21_PORT (or legacy RUN20_PORT) to force a specific UI port.
#   - Reads .run_backend_port unless RUN21_API_URL is provided explicitly.
#   - Falls back to a free frontend port in the 3000-3010 range when the
#     desired port is already occupied.
#   - Runs npm install automatically when node_modules is missing.
#   - Exports NEXT_PUBLIC_API_URL so the frontend build/runtime can talk to
#     the backend selected by the backend launcher.
#
# Environment variables:
#   - RUN21_PORT: force the frontend UI port.
#   - RUN20_PORT: legacy alias for the frontend UI port.
#   - RUN21_API_URL: force the backend API base URL and skip sync-file lookup.
#
# Notes:
#   - Start run20 first when you want automatic API URL synchronization.
#   - This script is the frontend half of the local no-Docker workflow.
# ------------------------------------------------------------------------------

set -euo pipefail

PORT="${RUN21_PORT:-${RUN20_PORT:-3000}}"
API_URL="http://127.0.0.1:8502"
ROOT="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$ROOT/frontend"
BACKEND_PORT_FILE="$ROOT/.run_backend_port"
PORT_FROM_USER="0"

if [ -n "${RUN21_PORT:-}" ] || [ -n "${RUN20_PORT:-}" ]; then
  PORT_FROM_USER="1"
fi

if [ -n "${RUN21_API_URL:-}" ]; then
  API_URL="$RUN21_API_URL"
elif [ -f "$BACKEND_PORT_FILE" ]; then
  BACKEND_PORT="$(tr -d '\r\n' < "$BACKEND_PORT_FILE")"
  if [ -n "$BACKEND_PORT" ]; then
    API_URL="http://127.0.0.1:${BACKEND_PORT}"
  fi
fi

if [ ! -f "$FRONTEND_DIR/package.json" ]; then
  echo "[Error] frontend package.json not found: $FRONTEND_DIR/package.json" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "[Error] npm is not installed or not in PATH." >&2
  echo "        Install Node.js first: https://nodejs.org/" >&2
  exit 1
fi

is_port_in_use() {
  local p="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$p" -sTCP:LISTEN -n -P >/dev/null 2>&1
    return $?
  fi
  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | grep -Eq ":[[:space:]]*${p}[[:space:]]"
    return $?
  fi
  return 1
}

if is_port_in_use "$PORT"; then
  if [ "$PORT_FROM_USER" = "1" ]; then
    echo "[Error] Port $PORT is already in use." >&2
    echo "        Change RUN21_PORT/RUN20_PORT or stop the process using this port." >&2
    exit 1
  fi

  FREE_PORT=""
  for p in $(seq 3000 3010); do
    if ! is_port_in_use "$p"; then
      FREE_PORT="$p"
      break
    fi
  done

  if [ -z "$FREE_PORT" ]; then
    echo "[Error] No free port found in range 3000-3010." >&2
    echo "        Stop conflicting processes or set RUN20_PORT to another free port." >&2
    exit 1
  fi

  echo "[Warn] Port 3000 is already in use. Falling back to port $FREE_PORT."
  PORT="$FREE_PORT"
fi

echo "Starting Frontend GUI on http://127.0.0.1:${PORT} ..."
echo "API target: ${API_URL}"
echo "Note: Start backend first with run20_start_backend_W.O._docker.sh"
echo "Press Ctrl+C to stop."
echo

cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
  echo "[Info] node_modules not found. Running npm install..."
  npm install
fi

export NEXT_PUBLIC_API_URL="$API_URL"

# Open browser in background if possible
if command -v xdg-open &>/dev/null; then
  sleep 1 && xdg-open "http://127.0.0.1:${PORT}" &
elif command -v open &>/dev/null; then
  sleep 1 && open "http://127.0.0.1:${PORT}" &
fi

npm run dev -- --hostname 127.0.0.1 --port "${PORT}"
