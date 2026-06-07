#!/usr/bin/env bash                                          # Use bash to run this script.
set -euo pipefail                                            # Stop on error, undefined variable, or pipe failure.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"                     # Project root is the parent folder of scripts.
cd "$ROOT"                                                   # Move to the project root.

echo "=========================================================" # Print title separator.
echo "[run10] Create Python virtual environment with uv"       # Print script purpose.
echo "=========================================================" # Print title separator.
echo "Root: $PWD"                                             # Show current project root.

command -v uv >/dev/null 2>&1 || {                            # Check whether uv command exists.
  echo "[ERROR] uv command was not found." >&2                 # Explain the error.
  exit 1                                                      # Exit with error.
}                                                             # End uv existence check.

uv venv                                                       # Create .venv in the project root.

echo                                                          # Print blank line.
echo "[OK] .venv was created or already exists."               # Show success message.
