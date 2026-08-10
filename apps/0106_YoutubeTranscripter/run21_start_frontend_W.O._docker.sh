#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# Purpose:
#   Start the local Next.js frontend without Docker and automatically point it
#   at the backend port selected by run20_start_backend_W.O._docker.sh.
#
# What this script does:
#   - Sets the frontend UI port to 3000 by default.
#   - Allows RUN21_PORT (or legacy RUN20_PORT) to force a specific UI port.
#   - Reads backend API port from .run_backend_port.
#   - Fails fast when .run_backend_port is missing or empty.
#   - Falls back to a free frontend port in the 3000-3010 range when the
#     desired port is already occupied.
#   - Installs frontend deps only when needed (first run or lockfile changed).
#   - Exports NEXT_PUBLIC_API_URL so the frontend build/runtime can talk to
#     the backend selected by the backend launcher.
#
# Environment variables:
#   - RUN21_PORT: force the frontend UI port.
#   - RUN20_PORT: legacy alias for the frontend UI port.
#   - RUN21_REQUIRE_HEALTH: 1=require backend /health status=healthy (default), 0=skip.
#
# Notes:
#   - Start run20 first when you want automatic API URL synchronization.
#   - This script is the frontend half of the local no-Docker workflow.
# ------------------------------------------------------------------------------

set -euo pipefail

PORT="${RUN21_PORT:-${RUN20_PORT:-3000}}"
API_URL=""
ROOT="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$ROOT/frontend"
BACKEND_PORT_FILE="$ROOT/.run_backend_port"
NPM_HASH_CACHE_FILE="$FRONTEND_DIR/.run21_npm_lock.sha256"
PORT_FROM_USER="0"
RUN21_REQUIRE_HEALTH="${RUN21_REQUIRE_HEALTH:-1}"

if [ -n "${RUN21_PORT:-}" ] || [ -n "${RUN20_PORT:-}" ]; then
  PORT_FROM_USER="1"
fi

if [ -f "$BACKEND_PORT_FILE" ]; then
  BACKEND_PORT="$(tr -d '\r\n' < "$BACKEND_PORT_FILE")"
  if [ -n "$BACKEND_PORT" ]; then
    API_URL="http://127.0.0.1:${BACKEND_PORT}"
  fi
fi

if [ -z "$API_URL" ]; then
  echo "[Error] Backend API URL is not resolved." >&2
  echo "        Start run20_start_backend_W.O._docker.sh first." >&2
  exit 1
fi

if [ "$RUN21_REQUIRE_HEALTH" = "1" ]; then
  if ! command -v curl >/dev/null 2>&1; then
    echo "[Warn] curl not found. Skipping backend health check." >&2
  else
    HEALTH_JSON="$(curl -fsS --max-time 5 "$API_URL/health" 2>/dev/null || true)"
    if [ -z "$HEALTH_JSON" ]; then
      echo "[Error] Backend health check failed: $API_URL/health is unreachable." >&2
      echo "        Start backend dependencies (PostgreSQL/Redis/worker) and retry." >&2
      exit 1
    fi

    case "$HEALTH_JSON" in
      *"\"status\":\"healthy\""*)
        echo "[OK] Backend health is healthy."
        ;;
      *)
        echo "[Error] Backend health is not healthy: $HEALTH_JSON" >&2
        echo "        Start backend dependencies (PostgreSQL/Redis/worker) and retry." >&2
        exit 1
        ;;
    esac
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

compute_sha256() {
  local file="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$file" | awk '{print $1}'
    return 0
  fi
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$file" | awk '{print $1}'
    return 0
  fi
  return 1
}

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

CURRENT_LOCK_HASH=""
CACHED_LOCK_HASH=""
if [ -f "package-lock.json" ]; then
  if CURRENT_LOCK_HASH="$(compute_sha256 "package-lock.json")"; then
    if [ -f "$NPM_HASH_CACHE_FILE" ]; then
      CACHED_LOCK_HASH="$(tr -d '\r\n' < "$NPM_HASH_CACHE_FILE")"
    fi
  else
    echo "[Warn] sha256 command not found. Falling back to node_modules existence check."
  fi
fi

NEED_INSTALL="0"
if [ ! -d "node_modules" ]; then
  NEED_INSTALL="1"
elif [ -n "$CURRENT_LOCK_HASH" ] && [ "$CURRENT_LOCK_HASH" != "$CACHED_LOCK_HASH" ]; then
  NEED_INSTALL="1"
fi

if [ "$NEED_INSTALL" = "1" ]; then
  if [ -f "package-lock.json" ]; then
    echo "[Info] Installing frontend dependencies (npm ci)..."
    npm ci --no-audit --fund=false
  else
    echo "[Info] package-lock.json not found. Running npm install..."
    npm install --no-audit --fund=false
  fi

  if [ -n "$CURRENT_LOCK_HASH" ]; then
    printf '%s\n' "$CURRENT_LOCK_HASH" > "$NPM_HASH_CACHE_FILE"
  fi
else
  echo "[Info] Frontend dependencies are up-to-date. Skipping npm install."
fi

export NEXT_PUBLIC_API_URL="$API_URL"

# Open browser in background if possible
if command -v xdg-open &>/dev/null; then
  sleep 1 && xdg-open "http://127.0.0.1:${PORT}" &
elif command -v open &>/dev/null; then
  sleep 1 && open "http://127.0.0.1:${PORT}" &
fi

npm run dev -- --hostname 127.0.0.1 --port "${PORT}"
