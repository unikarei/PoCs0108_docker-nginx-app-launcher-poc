#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# Purpose:
#   Create or validate the local Python virtual environment used by the uv-
#   based workflow for this repository.
#
# What this script does:
#   - Creates .venv with Python 3.11 when no usable environment exists.
#   - Detects the Windows-style .venv/Scripts/python.exe path as well as the
#     POSIX .venv/bin/python path so the same script works in mixed shells.
#   - Recreates the environment only when a Python version mismatch is detected.
#
# What this script does not do:
#   - It does not install dependencies.
#   - It does not start application processes.
#
# Typical next step after a successful run:
#   - ./run11_uv_sync.sh
#   - then ./run20_start_backend_W.O._docker.sh and ./run21_start_frontend_W.O._docker.sh
# ------------------------------------------------------------------------------
set -euo pipefail
RUN10_SCRIPT_VERSION="v0.1.0"
PY_TARGET="3.11"

if [ "$0" != "${BASH_SOURCE[0]}" ]; then
    printf 'Error: run10_uv_venv.sh must be executed directly, not sourced.\n' >&2
    return 1 2>/dev/null || exit 1
fi

cd "$(dirname "$0")" || exit 1
VENV_DIR="$(pwd)/.venv"
VENV_PY_WINDOWS="$VENV_DIR/Scripts/python.exe"
VENV_PY_POSIX="$VENV_DIR/bin/python"

if ! command -v uv >/dev/null 2>&1; then
    echo "[Error] uv is not installed or not in PATH." >&2
    echo "        Install uv first: https://docs.astral.sh/uv/" >&2
    exit 1
fi

cat <<EOF
========================================
         uv venv - Create Virtual Env
========================================
Script version : $RUN10_SCRIPT_VERSION
Project root   : $(pwd)
Venv path      : $VENV_DIR
Python target  : $PY_TARGET

EOF

if [ -x "$VENV_PY_WINDOWS" ]; then
    VENV_PY="$VENV_PY_WINDOWS"
elif [ -x "$VENV_PY_POSIX" ]; then
    VENV_PY="$VENV_PY_POSIX"
else
    VENV_PY=""
fi

if [ -n "$VENV_PY" ]; then
    VENV_PYVER="$($VENV_PY -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
    if [ "$VENV_PYVER" != "$PY_TARGET" ]; then
        echo "[Warn] Existing .venv uses Python $VENV_PYVER. Recreating for $PY_TARGET..."
        rm -rf "$VENV_DIR"
        uv venv .venv --python "$PY_TARGET"
    else
        echo "[OK] Existing virtual environment found."
    fi
else
    echo "Running: uv venv .venv --python $PY_TARGET"
    uv venv .venv --python "$PY_TARGET"
fi

echo
echo "Done! Next step:"
echo "  source .venv/bin/activate  # or .venv/Scripts/activate on Git Bash for Windows venvs"
echo "Then run:"
echo "  ./run11_uv_sync.sh"
    echo "  ./run20_start_backend_W.O._docker.sh"
    echo "  ./run21_start_frontend_W.O._docker.sh"
