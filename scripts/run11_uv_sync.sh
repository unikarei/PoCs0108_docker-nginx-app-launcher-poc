#!/usr/bin/env bash                                          # Use bash to run this script.
set -euo pipefail                                            # Stop on error, undefined variable, or pipe failure.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"                     # Project root is the parent folder of scripts.
VENV_PY="$ROOT/.venv/bin/python"                             # Python interpreter inside root .venv.
cd "$ROOT"                                                   # Move to the project root.

echo "=========================================================" # Print title separator.
echo "[run11] Sync Python dependencies with uv"                # Print script purpose.
echo "=========================================================" # Print title separator.

command -v uv >/dev/null 2>&1 || {                            # Check whether uv command exists.
  echo "[ERROR] uv command was not found." >&2                 # Explain the error.
  exit 1                                                      # Exit with error.
}                                                             # End uv existence check.

test -x "$VENV_PY" || {                                       # Check whether .venv Python exists.
  echo "[ERROR] .venv was not found." >&2                     # Explain the error.
  echo "Run scripts/run10_uv_venv.sh first." >&2              # Show next action.
  exit 1                                                      # Exit with error.
}                                                             # End .venv existence check.

if [ -f "pyproject.toml" ]; then                              # Prefer root pyproject when it exists.
  uv sync                                                     # Synchronize root project dependencies.
else                                                          # Use requirements files when no pyproject exists.
  [ -f "manager-api/requirements.txt" ] && uv pip install -r "manager-api/requirements.txt"    # Install Manager API dependencies.
  [ -f "launcher/requirements.txt" ] && uv pip install -r "launcher/requirements.txt"          # Install Launcher dependencies.
  [ -f "apps/app1/requirements.txt" ] && uv pip install -r "apps/app1/requirements.txt"        # Install App1 dependencies.
  [ -f "apps/app2/requirements.txt" ] && uv pip install -r "apps/app2/requirements.txt"        # Install App2 dependencies.
  [ -f "apps/app3/requirements.txt" ] && uv pip install -r "apps/app3/requirements.txt"        # Install App3 dependencies.
fi                                                            # End dependency selection.

echo                                                          # Print blank line.
echo "[OK] Dependency sync finished."                          # Show success message.
