#!/bin/bash

set -euo pipefail

# run02_app.sh is the top-level local launcher for this repository.
# It does not implement application logic itself; instead it selects one of the
# startup modes exposed by start_app.sh and then hands control over to it.
#
# Behavior:
# - backend: start only the API/backend side.
# - docker-frontend: start backend + Docker-based frontend (default).
# - local-frontend: start backend + local Node-based frontend.
#
# This wrapper is intentionally thin so that the real startup policy stays in
# start_app.sh and only the mode-selection surface lives here.

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'HELP'
Help text for mode selection:
  ./run02_app.sh [mode]

mode:
  backend           バックエンドのみ起動
  docker-frontend   バックエンド + フロント(Docker)  ※デフォルト
  local-frontend    バックエンド + フロント(ローカルNode)

例:
  OPEN_API_KEY="sk-proj-..." ./run02_app.sh
  OPEN_API_KEY="sk-proj-..." ./run02_app.sh backend
  OPEN_API_KEY="sk-proj-..." ./run02_app.sh local-frontend
HELP
  exit 0
fi

MODE="${1:-docker-frontend}"

case "$MODE" in
  backend)
    exec ./start_app.sh --no-build
    ;;
  docker-frontend)
    exec ./start_app.sh --with-frontend --no-build
    ;;
  local-frontend)
    exec ./start_app.sh --frontend-local --no-build
    ;;
  *)
    echo "Unknown mode: $MODE" >&2
    echo "Try: ./run02_app.sh --help" >&2
    exit 1
    ;;
esac
