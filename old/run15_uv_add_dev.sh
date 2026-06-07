#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# Purpose:
#   Add development-only dependencies to the project, either through uv's
#   dependency metadata or, when pyproject.toml is absent, directly into .venv.
#
# What this script does:
#   - Verifies that uv is available.
#   - Requires one or more package names as arguments.
#   - Uses uv add --group dev when pyproject.toml exists.
#   - Falls back to pip install inside .venv when the project is in requirements-
#     file mode instead of pyproject-managed mode.
#
# Typical usage:
#   - ./run15_uv_add_dev.sh ruff
#   - ./run15_uv_add_dev.sh mypy ruff
# ------------------------------------------------------------------------------
set -euo pipefail
RUN15_SCRIPT_VERSION="v0.1.0"

if [ "$0" != "${BASH_SOURCE[0]}" ]; then
    printf 'Error: run15_uv_add_dev.sh must be executed directly, not sourced.\n' >&2
    return 1 2>/dev/null || exit 1
fi

cd "$(dirname "$0")" || exit 1
ROOT="$(pwd)"
VENV_PY="$ROOT/.venv/bin/python"
PYPROJECT="$ROOT/pyproject.toml"

if ! command -v uv >/dev/null 2>&1; then
    echo "[Error] uv is not installed or not in PATH." >&2
    exit 1
fi

if [ $# -eq 0 ]; then
    echo "Usage: ./run15_uv_add_dev.sh <package> [package2 ...]"
    echo
    echo "Examples:"
    echo "  ./run15_uv_add_dev.sh ruff"
    echo "  ./run15_uv_add_dev.sh mypy ruff"
    exit 1
fi

cat <<EOF
========================================
      Add Dev Packages (--group dev)
========================================
Script version : $RUN15_SCRIPT_VERSION
Project root   : $ROOT

EOF

if [ -f "$PYPROJECT" ]; then
    echo "Running: uv add --group dev $*"
    uv add --group dev "$@"
else
    if [ ! -x "$VENV_PY" ]; then
        echo "[Info] .venv not found. Creating virtual environment first..."
        uv venv .venv
    fi
    if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
        echo "[Info] pip not found in .venv. Bootstrapping pip..."
        "$VENV_PY" -m ensurepip --upgrade
    fi
    echo "[Info] pyproject.toml not found. Installing packages into .venv only."
    echo "Running: $VENV_PY -m pip install $*"
    "$VENV_PY" -m pip install "$@"
fi
echo
echo "[OK] Dev dependency added successfully."
