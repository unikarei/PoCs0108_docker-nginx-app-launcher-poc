#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# Purpose:
#   Start the local FastAPI backend without Docker, using uvicorn with
#   --reload for development.
#
# What this script does:
#   - Verifies the backend source file and local .venv interpreter exist.
#   - Uses the default backend port 8502 unless RUN20_BACKEND_PORT is set.
#   - If the requested port is occupied and the port came from the default or
#     from auto-selection, scans 8502-8515 for the first free port.
#   - Writes the selected backend port into .run_backend_port so the frontend
#     launcher can automatically point to the correct API URL.
#   - Starts uvicorn with --reload for iterative development.
#
# Environment variables:
#   - RUN20_BACKEND_PORT: force a specific backend port.
#
# Notes:
#   - This script is the backend half of the local no-Docker workflow.
#   - run21_start_frontend_W.O._docker.sh reads the port sync file that this
#     script writes.
# ------------------------------------------------------------------------------
set -euo pipefail
RUN20_SCRIPT_VERSION="v0.2.0"

if [ "$0" != "${BASH_SOURCE[0]}" ]; then
    printf 'Error: run20_start_backend_W.O._docker.sh must be executed directly, not sourced.\n' >&2
    return 1 2>/dev/null || exit 1
fi

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT/backend"
if [ -x "$ROOT/.venv/Scripts/python.exe" ]; then
    VENV_PY="$ROOT/.venv/Scripts/python.exe"
else
    VENV_PY="$ROOT/.venv/bin/python"
fi
UVICORN_HOST="127.0.0.1"
UVICORN_PORT="${RUN20_BACKEND_PORT:-8502}"
PORT_FROM_USER="0"
PORT_SYNC_FILE="$ROOT/.run_backend_port"

# Local launcher normalization:
# Prefer DATABASE_URL from repo .env to avoid inheriting stale shell values.
# If it uses docker style host (@postgres), rewrite only the host part to
# localhost so host-side run20 can connect to published port 5432.
if [ -f "$ROOT/.env" ]; then
    DB_URL_FROM_ENV_FILE="$(grep -E '^DATABASE_URL=' "$ROOT/.env" | tail -n 1 | cut -d'=' -f2-)"
    if [ -n "$DB_URL_FROM_ENV_FILE" ]; then
        export DATABASE_URL="$DB_URL_FROM_ENV_FILE"
    fi
fi

if [ -n "${DATABASE_URL:-}" ]; then
    case "$DATABASE_URL" in
        *@postgres:*)
            export DATABASE_URL="${DATABASE_URL/@postgres:/@127.0.0.1:}"
            ;;
    esac
fi

if [ -n "${RUN20_BACKEND_PORT:-}" ]; then
    PORT_FROM_USER="1"
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
    if command -v netstat >/dev/null 2>&1; then
        netstat -an 2>/dev/null | grep -Eq ":${p}[[:space:]]+.*LISTEN"
        return $?
    fi
    return 1
}

cd "$ROOT" || exit 1

if [ ! -f "$BACKEND_DIR/main.py" ]; then
    echo "[Error] backend main module not found: $BACKEND_DIR/main.py" >&2
    exit 1
fi

if [ ! -x "$VENV_PY" ]; then
    echo "[Error] .venv python not found: $VENV_PY" >&2
    echo "        Run run10_uv_venv.sh and run11_uv_sync.sh first." >&2
    exit 1
fi

cat <<EOF
========================================
    Start YouTube Transcription FastAPI
========================================
Script version : $RUN20_SCRIPT_VERSION
Root           : $ROOT
Backend dir    : $BACKEND_DIR
Venv python    : $VENV_PY

EOF

if is_port_in_use "$UVICORN_PORT"; then
    if [ "$PORT_FROM_USER" = "1" ]; then
        echo "[Error] Backend port $UVICORN_PORT is already in use." >&2
        echo "        Change RUN20_BACKEND_PORT or stop the process using this port." >&2
        exit 1
    fi

    FREE_PORT=""
    for p in $(seq 8502 8515); do
        if ! is_port_in_use "$p"; then
            FREE_PORT="$p"
            break
        fi
    done

    if [ -z "$FREE_PORT" ]; then
        echo "[Error] No free backend port found in range 8502-8515." >&2
        echo "        Stop conflicting processes or set RUN20_BACKEND_PORT." >&2
        exit 1
    fi

    echo "[Warn] Backend port 8502 is already in use. Falling back to $FREE_PORT."
    UVICORN_PORT="$FREE_PORT"
fi

printf '%s\n' "$UVICORN_PORT" > "$PORT_SYNC_FILE"
echo "URL            : http://$UVICORN_HOST:$UVICORN_PORT/"
echo "Sync file      : $PORT_SYNC_FILE"
echo

echo "Running FastAPI app with auto-reload..."
cd "$BACKEND_DIR"
"$VENV_PY" -m uvicorn main:app --reload --host "$UVICORN_HOST" --port "$UVICORN_PORT"
