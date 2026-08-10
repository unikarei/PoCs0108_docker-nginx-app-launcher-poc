#!/usr/bin/env bash
set -euo pipefail                              # エラー時停止(-e)・未定義変数エラー(-u)・パイプ失敗検出(pipefail)

cd "$(dirname "$0")"                         # スクリプト自身のディレクトリへ移動（実行場所に依存しない）

# ------------------------------------------------------------
# 使い方表示（--help / -h のときに表示するメッセージ）
# ------------------------------------------------------------

usage() {
  cat <<'EOF'                                  # Usage文字列を標準出力へ（'EOF' なので変数展開しない）
Usage:
  ./start_app.sh [--foreground] [--no-build] [--logs] [--with-frontend]

Starts the backend stack via Docker Compose (postgres, redis, migrate, api, worker).

Options:
  --foreground     Run docker compose in the foreground (no -d)
  --no-build       Do not rebuild images
  --logs           After starting (detached), follow api/worker logs
  --with-frontend  Also start Next.js dev server (opens http://localhost:3000)
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then  # 先頭引数がヘルプなら…（引数なしでも安全に評価）
  usage                                        # 使い方を表示
  exit 0                                       # 正常終了
fi

# ------------------------------------------------------------
# .env の読み込み（特に OPENAI_API_KEY）
# - docker compose も .env は自動読込するが、ここでは必須値の検証のために読み込む
# - Windows由来のCRLF(\r)を除去して source できるようにする
# ------------------------------------------------------------
if [[ -f .env ]]; then                          # .env が存在する場合のみ
  set -a                                        # 以降に定義される変数を自動 export
  # shellcheck disable=SC1090                   # 動的source（プロセス置換）を許容
  source <(sed 's/\r$//' .env)                  # 行末の \r を落としてから読み込み
  set +a                                        # 自動 export を解除
fi

# 優先順位: 環境変数 OPENAI_API_KEY > OPEN_API_KEY > ~/.openai_api_key ファイル
# 1) OPEN_API_KEY は OPENAI_API_KEY の互換名
if [[ -z "${OPENAI_API_KEY:-}" && -n "${OPEN_API_KEY:-}" ]]; then
  export OPENAI_API_KEY="$OPEN_API_KEY"
  echo "INFO: OPEN_API_KEY を OPENAI_API_KEY として使用します。" >&2
fi

# 2) ~/.openai_api_key ファイルから読み込む（1行目をキーとして使用）
KEY_FILE="${HOME}/.openai_api_key"
if [[ -z "${OPENAI_API_KEY:-}" && -f "$KEY_FILE" ]]; then
  OPENAI_API_KEY="$(head -1 "$KEY_FILE" | tr -d '\r\n')"
  export OPENAI_API_KEY
  echo "INFO: APIキーを ${KEY_FILE} から読み込みました。" >&2
fi

# 3) どこにもキーがなければ対話的に入力を促す
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  if [[ -t 0 ]]; then
    echo "" >&2
    echo "OPENAI_API_KEY が設定されていません。" >&2
    echo "OpenAI APIキー (sk-proj-...) を入力してください:" >&2
    read -r -s OPENAI_API_KEY
    export OPENAI_API_KEY
    echo "" >&2
    read -r -p "~/.openai_api_key に保存しますか？ [y/N]: " SAVE_KEY
    if [[ "${SAVE_KEY:-}" =~ ^[Yy]$ ]]; then
      echo "$OPENAI_API_KEY" > "$KEY_FILE"
      chmod 600 "$KEY_FILE"
      echo "INFO: APIキーを ${KEY_FILE} に保存しました。次回から自動読み込みします。" >&2
    fi
  else
    echo "ERROR: OPENAI_API_KEY is not set." >&2
    echo "- export OPENAI_API_KEY=..." >&2
    echo "- or export OPEN_API_KEY=..." >&2
    echo "- or store key in ~/.openai_api_key" >&2
    exit 1
  fi
fi

# ------------------------------------------------------------
# Docker の起動確認（Windows/WSL: Docker Desktop を自動起動して待つ）
# - Git Bash / MSYS / Cygwin / WSL で実行されるケースを想定
# - Linux/macOS はメッセージを出して終了（勝手に起動しない）
# ------------------------------------------------------------
is_windows_like() {
  case "$(uname -s 2>/dev/null || true)" in
    MINGW*|MSYS*|CYGWIN*) return 0 ;;
  esac
  if [[ -r /proc/version ]] && grep -qi microsoft /proc/version 2>/dev/null; then
    return 0
  fi
  return 1
}

docker_daemon_ready() {
  docker info >/dev/null 2>&1
}

open_url() {
  local url="$1"

  if command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "Start-Process '$url'" \
      >/dev/null 2>&1 || true
    return 0
  fi

  if command -v cmd.exe >/dev/null 2>&1; then
    cmd.exe /c "start \"\" \"$url\"" >/dev/null 2>&1 || true
    return 0
  fi

  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 || true
    return 0
  fi

  if command -v open >/dev/null 2>&1; then
    open "$url" >/dev/null 2>&1 || true
    return 0
  fi

  echo "INFO: Please open: $url" >&2
  return 0
}

start_docker_desktop() {
  if command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command '
$p1Base = [System.Environment]::GetEnvironmentVariable("ProgramFiles")
$p2Base = [System.Environment]::GetEnvironmentVariable("ProgramFiles(x86)")
$p1 = Join-Path $p1Base "Docker\Docker\Docker Desktop.exe"
$p2 = if ($p2Base) { Join-Path $p2Base "Docker\Docker\Docker Desktop.exe" } else { $null }
if (Test-Path $p1) { Start-Process -FilePath $p1 | Out-Null; exit 0 }
elseif ($p2 -and (Test-Path $p2)) { Start-Process -FilePath $p2 | Out-Null; exit 0 }
else { exit 2 }
' >/dev/null 2>&1
    return $?
  fi

  if command -v cmd.exe >/dev/null 2>&1; then
    cmd.exe /c "start \"\" \"%ProgramFiles%\\Docker\\Docker\\Docker Desktop.exe\"" >/dev/null 2>&1 && return 0
    cmd.exe /c "start \"\" \"%ProgramFiles(x86)%\\Docker\\Docker\\Docker Desktop.exe\"" >/dev/null 2>&1 && return 0
    return 2
  fi

  return 127
}

if command -v docker >/dev/null 2>&1; then
  if ! docker_daemon_ready; then
    if is_windows_like; then
      echo "Docker daemon is not reachable. Trying to start Docker Desktop..." >&2
      if ! start_docker_desktop; then
        echo "ERROR: Failed to start Docker Desktop automatically." >&2
        echo "- Please start Docker Desktop manually and retry." >&2
        exit 1
      fi
      echo "Waiting for Docker to become ready..." >&2
      for _ in {1..60}; do
        if docker_daemon_ready; then
          break
        fi
        sleep 2
      done
      if ! docker_daemon_ready; then
        echo "ERROR: Docker Desktop did not become ready in time." >&2
        echo "- Please check Docker Desktop status and retry." >&2
        exit 1
      fi
    else
      echo "ERROR: Docker is not running (docker daemon unreachable)." >&2
      echo "- Start Docker and retry." >&2
      exit 1
    fi
  fi
fi

# ------------------------------------------------------------
# docker compose コマンドの決定
# - v2: `docker compose`
# - 互換: `docker-compose`
# ------------------------------------------------------------
if docker compose version >/dev/null 2>&1; then  # docker compose(v2) が使えるなら
  DC=(docker compose)                            # 実行コマンドを配列で保持（空白を安全に扱う）
elif command -v docker-compose >/dev/null 2>&1; then  # docker-compose(v1系) があるなら
  DC=(docker-compose)                            # こちらを採用
else
  echo "ERROR: docker compose (v2) or docker-compose is required." >&2  # どちらも無ければ実行不可
  exit 1                                        # 失敗終了
fi

DETACH=1                                        # 1: detach(-d)で起動 / 0: フォアグラウンド
BUILD=1                                         # 1: --build を付ける / 0: 付けない
FOLLOW_LOGS=0                                   # 1: 起動後に logs -f を実行
WITH_FRONTEND_DOCKER=0                          # 1: frontend サービスも起動
WITH_FRONTEND_LOCAL=0                           # 1: frontend をローカル npm で起動

# ------------------------------------------------------------
# 引数解析（フラグのみ対応）
# ------------------------------------------------------------
for arg in "$@"; do                             # すべての引数を順に評価
  case "$arg" in                               # 引数ごとに分岐
    --foreground)
      DETACH=0                                  # -d を付けない（composeをフォアグラウンドで）
      ;;
    --no-build)
      BUILD=0                                   # イメージを再ビルドしない
      ;;
    --logs)
      FOLLOW_LOGS=1                              # 起動後にログ追従する
      ;;
    --with-frontend)
      WITH_FRONTEND_DOCKER=1                     # frontend コンテナも起動対象に入れる
      ;;
    --frontend-local)
      WITH_FRONTEND_LOCAL=1                      # frontend をローカル npm で起動
      ;;
    *)
      echo "Unknown option: $arg" >&2           # 未知の引数はエラー
      usage                                      # 使い方を表示
      exit 2                                     # 使い方の誤り（一般的に2）
      ;;
  esac
done

if [[ $WITH_FRONTEND_DOCKER -eq 1 && $WITH_FRONTEND_LOCAL -eq 1 ]]; then
  echo "ERROR: --with-frontend and --frontend-local cannot be used together." >&2
  exit 2
fi

UP_ARGS=(up)                                    # docker compose の subcommand を配列で構築
if [[ $DETACH -eq 1 ]]; then                     # detach指定なら
  UP_ARGS+=(-d)                                  # `up -d`
fi
if [[ $BUILD -eq 1 ]]; then                      # build指定なら
  UP_ARGS+=(--build)                             # `--build` を付与
fi

SERVICES=(postgres redis migrate api worker)     # 起動するサービス一覧（compose.yml 側の定義名）
if [[ $WITH_FRONTEND_DOCKER -eq 1 ]]; then
  SERVICES+=(frontend)
fi

# ------------------------------------------------------------
# 起動処理（compose up → 状態確認 → 必要ならログ追従）
# ------------------------------------------------------------
"${DC[@]}" "${UP_ARGS[@]}" "${SERVICES[@]}"      # compose を起動（配列展開で安全に引数を渡す）

"${DC[@]}" ps                                  # 起動状態を表示（Up/healthy を確認）

echo                                            # 1行空ける
echo "Backend is starting."                    # 起動案内
echo "- API:  http://localhost:8000"           # API URL
echo "- Docs: http://localhost:8000/docs"      # Swagger URL
echo                                            # 1行空ける

# ------------------------------------------------------------
# フロントエンド起動 (--frontend-local 指定時)
# - frontend/ ディレクトリで npm run dev をバックグラウンド実行
# ------------------------------------------------------------
FRONTEND_PID_FILE=".frontend.pid"              # フロントエンドPIDファイル

if [[ $WITH_FRONTEND_LOCAL -eq 1 ]]; then        # フロント起動指定あり
  echo "Starting Next.js frontend..."
  
  # node_modules がなければ npm install を実行
  if [[ ! -d "frontend/node_modules" ]]; then
    echo "Installing frontend dependencies..."
    (cd frontend && npm install)
  fi
  
  # 既存のフロントエンドプロセスを停止
  if [[ -f "$FRONTEND_PID_FILE" ]]; then
    OLD_PID=$(cat "$FRONTEND_PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
      echo "Stopping previous frontend process (PID: $OLD_PID)..."
      kill "$OLD_PID" 2>/dev/null || true
      sleep 1
    fi
    rm -f "$FRONTEND_PID_FILE"
  fi
  
  # フロントエンドをバックグラウンドで起動
  (cd frontend && npm run dev > ../frontend.log 2>&1) &
  FRONTEND_PID=$!
  echo $FRONTEND_PID > "$FRONTEND_PID_FILE"
  
  echo "Frontend started (PID: $FRONTEND_PID)"
  echo "- UI:   http://localhost:3000"
  echo "- Logs: tail -f frontend.log"
  echo
  
  # フロントエンドの起動を少し待つ
  sleep 3
  
  # ブラウザを開く
  open_url "http://localhost:3000"
fi

if [[ $DETACH -eq 1 && $FOLLOW_LOGS -eq 1 ]]; then  # detach起動かつ logs 指定なら
  "${DC[@]}" logs -f api worker                 # api/worker のログを追従
fi
