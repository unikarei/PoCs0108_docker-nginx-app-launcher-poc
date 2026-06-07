#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# Purpose:
#   Run the project's pytest suite through the uv-managed Python environment.
#
# What this script does:
#   - Verifies that uv is available.
#   - Uses .venv/Scripts/python.exe or .venv/bin/python when a local venv exists.
#   - Falls back to plain uv run when no local interpreter is available.
#   - Runs pytest -v by default when no arguments are provided.
#
# Typical usage:
#   - ./run14_uv_test.sh
#   - ./run14_uv_test.sh tests/test_example.py -k name
# ------------------------------------------------------------------------------
set -euo pipefail
RUN14_SCRIPT_VERSION="v0.1.0"

if [ "$0" != "${BASH_SOURCE[0]}" ]; then
	printf 'Error: run14_uv_test.sh must be executed directly, not sourced.\n' >&2
	return 1 2>/dev/null || exit 1
fi

cd "$(dirname "$0")" || exit 1
ROOT="$(pwd)"
VENV_PY="$ROOT/.venv/bin/python"

if ! command -v uv >/dev/null 2>&1; then
	echo "[Error] uv is not installed or not in PATH." >&2
	exit 1
fi

cat <<EOF
========================================
			Run Tests with uv
========================================
Script version : $RUN14_SCRIPT_VERSION
Project root   : $ROOT

EOF

if [ $# -eq 0 ]; then
	if [ -x "$VENV_PY" ]; then
		echo "Running: uv run --python $VENV_PY pytest -v"
		uv run --python "$VENV_PY" pytest -v
	else
		echo "Running: uv run pytest -v"
		uv run pytest -v
	fi
else
	if [ -x "$VENV_PY" ]; then
		echo "Running: uv run --python $VENV_PY pytest $*"
		uv run --python "$VENV_PY" pytest "$@"
	else
		echo "Running: uv run pytest $*"
		uv run pytest "$@"
	fi
fi

echo
echo "[OK] Test command completed successfully."
