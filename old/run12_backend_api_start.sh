#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# Purpose: Start FastAPI server
#   Start FastAPI development server (uvicorn with --reload) for this project.
#   Intended as the primary local app startup entry point.
# ------------------------------------------------------------------------------
set -euo pipefail
RUN12_SCRIPT_VERSION="v0.1.0"

if [ "$0" != "${BASH_SOURCE[0]}" ]; then
    printf 'Error: run12_backend_api_start.sh must be executed directly, not sourced.\n' >&2
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
UVICORN_PORT="8502"

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
Script version : $RUN12_SCRIPT_VERSION
Root           : $ROOT
Backend dir    : $BACKEND_DIR
Venv python    : $VENV_PY
URL            : http://$UVICORN_HOST:$UVICORN_PORT/

EOF

echo "Running FastAPI app with auto-reload..."
cd "$BACKEND_DIR"
"$VENV_PY" -m uvicorn main:app --reload --host "$UVICORN_HOST" --port "$UVICORN_PORT"
