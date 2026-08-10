#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# ------------------------------------------------------------
# 使い方表示
# ------------------------------------------------------------
usage() {
  cat <<'EOF'
Usage:
  ./stop_app.sh [--all]

Stops the backend stack and optionally the frontend.

Options:
  --all    Also stop the frontend (Next.js dev server)
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

# ------------------------------------------------------------
# docker compose コマンドの決定
# ------------------------------------------------------------
if docker compose version >/dev/null 2>&1; then
  DC=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  DC=(docker-compose)
else
  echo "ERROR: docker compose (v2) or docker-compose is required." >&2
  exit 1
fi

STOP_FRONTEND=0

# ------------------------------------------------------------
# 引数解析
# ------------------------------------------------------------
for arg in "$@"; do
  case "$arg" in
    --all)
      STOP_FRONTEND=1
      ;;
    *)
      echo "Unknown option: $arg" >&2
      usage
      exit 2
      ;;
  esac
done

# ------------------------------------------------------------
# バックエンド停止
# ------------------------------------------------------------
echo "Stopping backend services..."
"${DC[@]}" down

# ------------------------------------------------------------
# フロントエンド停止 (--all 指定時)
# ------------------------------------------------------------
FRONTEND_PID_FILE=".frontend.pid"

if [[ $STOP_FRONTEND -eq 1 ]]; then
  if [[ -f "$FRONTEND_PID_FILE" ]]; then
    FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
    if kill -0 "$FRONTEND_PID" 2>/dev/null; then
      echo "Stopping frontend process (PID: $FRONTEND_PID)..."
      kill "$FRONTEND_PID" 2>/dev/null || true
      sleep 1
      # 強制終了が必要な場合
      if kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill -9 "$FRONTEND_PID" 2>/dev/null || true
      fi
    fi
    rm -f "$FRONTEND_PID_FILE"
    echo "Frontend stopped."
  else
    echo "No frontend process found (.frontend.pid not present)."
  fi
fi

echo "Done."
