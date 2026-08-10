#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# Purpose:
#   Synchronize the local .venv with the project dependency set recorded in
#   requirements.txt / uv-managed metadata.
#
# What this script does:
#   - Ensures uv is available.
#   - Creates .venv if it does not exist.
#   - Rebuilds .venv when the Python version is not the expected 3.11 line.
#   - Boots pip inside .venv if needed and installs project requirements.
#
# Typical usage:
#   - Run after ./run10_uv_venv.sh
#   - Re-run whenever dependencies change
# ------------------------------------------------------------------------------
set -euo pipefail
RUN11_SCRIPT_VERSION="v0.1.0"
PY_TARGET="3.11"

if [ "$0" != "${BASH_SOURCE[0]}" ]; then
	printf 'Error: run11_uv_sync.sh must be executed directly, not sourced.\n' >&2
	return 1 2>/dev/null || exit 1
fi

cd "$(dirname "$0")" || exit 1
ROOT="$(pwd)"
if [ -x "$ROOT/.venv/Scripts/python.exe" ]; then
	VENV_PY="$ROOT/.venv/Scripts/python.exe"
else
	VENV_PY="$ROOT/.venv/bin/python"
fi
REQ_FILE="$ROOT/requirements.txt"

if ! command -v uv >/dev/null 2>&1; then
	echo "[Error] uv is not installed or not in PATH." >&2
	echo "        Install uv first: https://docs.astral.sh/uv/" >&2
	exit 1
fi

cat <<EOF
========================================
	Install Dependencies (.venv)
========================================
Script version : $RUN11_SCRIPT_VERSION
Project root   : $ROOT

EOF

if [ ! -f "$REQ_FILE" ]; then
	echo "[Error] requirements.txt not found: $REQ_FILE" >&2
	exit 1
fi

if [ ! -x "$VENV_PY" ]; then
	echo "[Info] .venv not found. Creating virtual environment first..."
	uv venv .venv --python "$PY_TARGET"
	if [ -x "$ROOT/.venv/Scripts/python.exe" ]; then
		VENV_PY="$ROOT/.venv/Scripts/python.exe"
	else
		VENV_PY="$ROOT/.venv/bin/python"
	fi
fi

VENV_PYVER="$($VENV_PY -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
if [ "$VENV_PYVER" != "$PY_TARGET" ]; then
	echo "[Warn] Existing .venv uses Python $VENV_PYVER. Recreating for $PY_TARGET..."
	rm -rf "$ROOT/.venv"
	uv venv .venv --python "$PY_TARGET"
	if [ -x "$ROOT/.venv/Scripts/python.exe" ]; then
		VENV_PY="$ROOT/.venv/Scripts/python.exe"
	else
		VENV_PY="$ROOT/.venv/bin/python"
	fi
fi

if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
	echo "[Info] pip not found in .venv. Bootstrapping pip..."
	"$VENV_PY" -m ensurepip --upgrade
fi

echo "Running: $VENV_PY -m pip install --only-binary psycopg2-binary -r requirements.txt"
"$VENV_PY" -m pip install --only-binary psycopg2-binary -r requirements.txt
echo
echo "[OK] Dependency installation completed successfully."
