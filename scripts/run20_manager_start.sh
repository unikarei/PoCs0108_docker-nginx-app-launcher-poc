#!/usr/bin/env bash                                          # Use bash to run this script.
set -euo pipefail                                            # Stop on error, undefined variable, or pipe failure.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"                     # Project root is the parent folder of scripts.
MANAGER_DIR="$ROOT/manager-api"                              # Manager API folder.
VENV_PY="$ROOT/.venv/bin/python"                             # Python interpreter inside root .venv.
PID_DIR="$ROOT/.run"                                         # Runtime folder for PID files.
PID_FILE="$PID_DIR/manager-api.pid"                          # PID file for Manager API.
MANAGER_URL="http://127.0.0.1:9000/health"                   # Health URL for Manager API.
cd "$ROOT"                                                   # Move to the project root.

echo "=========================================================" # Print title separator.
echo "[run20] Start host-side Manager API"                     # Print script purpose.
echo "=========================================================" # Print title separator.

if curl -fsS "$MANAGER_URL" >/dev/null 2>&1; then             # Check whether Manager API is already running.
  echo "[OK] Manager API is already running."                  # Show existing status.
  echo "URL: $MANAGER_URL"                                    # Show health check URL.
  exit 0                                                      # Exit successfully.
fi                                                            # End already-running check.

test -f "$MANAGER_DIR/src/main.py" || {                       # Require Manager API source file.
  echo "[ERROR] Manager API source was not found." >&2         # Explain the error.
  echo "Missing: $MANAGER_DIR/src/main.py" >&2                # Show missing path.
  exit 1                                                      # Exit with error.
}                                                             # End source existence check.

mkdir -p "$PID_DIR"                                          # Create runtime folder if missing.

if [ -x "$VENV_PY" ]; then                                    # Use .venv Python when available.
  PYTHON_EXE="$VENV_PY"                                      # Store .venv Python path.
else                                                          # Fall back when .venv does not exist.
  PYTHON_EXE="python"                                        # Use system Python command.
fi                                                            # End Python selection.

cd "$MANAGER_DIR"                                            # Move into Manager API folder.
nohup "$PYTHON_EXE" -m uvicorn src.main:app --host 127.0.0.1 --port 9000 > "$ROOT/.run/manager-api.log" 2>&1 & # Start Manager API in background.
echo "$!" > "$PID_FILE"                                      # Save background process PID.
cd "$ROOT"                                                   # Return to project root.

echo                                                          # Print blank line.
echo "[OK] Manager API start command was issued."              # Show success message.
echo "PID: $(cat "$PID_FILE")"                                # Show saved PID.
echo "URL: http://127.0.0.1:9000/health"                      # Show health check URL.
