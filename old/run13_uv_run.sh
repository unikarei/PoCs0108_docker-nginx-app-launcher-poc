#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# Purpose:
#   Execute an arbitrary command through the repository's uv-managed Python
#   environment without requiring manual activation of .venv.
#
# What this script does:
#   - Verifies that uv is available.
#   - Uses .venv/Scripts/python.exe or .venv/bin/python when a local venv exists.
#   - Falls back to plain uv run when no local interpreter is available.
#
# Typical usage:
#   - ./run13_uv_run.sh python -m pip list
#   - ./run13_uv_run.sh pytest -v
# ------------------------------------------------------------------------------
set -euo pipefail
RUN13_SCRIPT_VERSION="v0.1.0"

if [ "$0" != "${BASH_SOURCE[0]}" ]; then
    printf 'Error: run13_uv_run.sh must be executed directly, not sourced.\n' >&2
    return 1 2>/dev/null || exit 1
fi

cd "$(dirname "$0")" || exit 1
ROOT="$(pwd)"
VENV_PY="$ROOT/.venv/bin/python"

if ! command -v uv >/dev/null 2>&1; then
    echo "[Error] uv is not installed or not in PATH." >&2
    exit 1
fi

if [ $# -eq 0 ]; then
    echo "Usage: ./run13_uv_run.sh <command> [args ...]"
    echo
    echo "Examples:"
    echo "  ./run13_uv_run.sh python -m pip list"
    echo "  ./run13_uv_run.sh pytest tests/test_phase1_api.py -v"
    exit 1
fi

cat <<EOF
========================================
           uv run passthrough
========================================
Script version : $RUN13_SCRIPT_VERSION
Project root   : $ROOT

EOF

if [ -x "$VENV_PY" ]; then
    echo "Running: uv run --python $VENV_PY $*"
    uv run --python "$VENV_PY" "$@"
else
    echo "Running: uv run $*"
    uv run "$@"
fi
echo
echo "[OK] uv run command completed successfully."
