#!/usr/bin/env bash
set -euo pipefail                                            # Stop on error, undefined variable, or pipe failure.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"                  # Directory that contains this script.
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"                         # Project root is the parent folder of scripts.
cd "$ROOT"                                                   # Move to the project root.

SKIP_INIT=0                                                   # Run Docker/project checks by default.
SKIP_MANAGER=0                                                # Start or verify Manager API by default.
SKIP_DATABASE=0                                               # Start external database by default.
NO_BUILD=0                                                    # Rebuild images by default for backward compatibility.
SKIP_STATUS=0                                                 # Show Compose status by default.
SKIP_WORKER_CHECK=0                                           # Verify worker health by default.

print_help() {
  echo "Usage: run50_start_all.sh [options]"
  echo "  --quick              Skip init, database start, status, and image build."
  echo "  --skip-init          Skip Docker/project file checks."
  echo "  --skip-manager       Skip Manager API start/check."
  echo "  --skip-database      Skip external database start."
  echo "  --no-build           Start containers without rebuilding images."
  echo "  --skip-status        Skip Docker Compose status display."
  echo "  --skip-worker-check  Skip YouTube worker health polling."
}

while (($# > 0)); do
  case "$1" in
    --quick)
      SKIP_INIT=1
      SKIP_DATABASE=1
      NO_BUILD=1
      SKIP_STATUS=1
      ;;
    --skip-init) SKIP_INIT=1 ;;
    --skip-manager) SKIP_MANAGER=1 ;;
    --skip-database) SKIP_DATABASE=1 ;;
    --no-build) NO_BUILD=1 ;;
    --skip-status) SKIP_STATUS=1 ;;
    --skip-worker-check) SKIP_WORKER_CHECK=1 ;;
    --help) print_help; exit 0 ;;
    *) echo "[ERROR] Unknown option: $1" >&2; print_help; exit 2 ;;
  esac
  shift
done

echo "=========================================================" # Print title separator.
echo "[run50] Start all services"                              # Print script purpose.
echo "=========================================================" # Print title separator.

if ((SKIP_INIT == 0)); then "$SCRIPT_DIR/run30_docker_init.sh"; else echo "[SKIP] Docker/project check."; fi
if ((SKIP_MANAGER == 0)); then "$SCRIPT_DIR/run20_manager_start.sh"; else echo "[SKIP] Manager API start."; fi
if ((SKIP_MANAGER == 0)); then sleep 3; fi                    # Wait for Manager API startup only when it was started.
if ((SKIP_DATABASE == 0)); then "$SCRIPT_DIR/run25_database_start.sh"; else echo "[SKIP] External database start."; fi

DOCKER_OPTIONS=(--skip-database)
if ((NO_BUILD == 1)); then DOCKER_OPTIONS+=(--no-build); fi
"$SCRIPT_DIR/run32_docker_start_detached.sh" "${DOCKER_OPTIONS[@]}" # Start Docker services in background.
if ((SKIP_STATUS == 0)); then "$SCRIPT_DIR/run35_docker_status.sh"; else echo "[SKIP] Docker service status."; fi
if ((SKIP_WORKER_CHECK == 0)); then "$SCRIPT_DIR/run43_youtube_worker_check.sh"; else echo "[SKIP] YouTube worker health check."; fi

echo                                                         # Print blank line.
echo "[OK] All start commands finished."                     # Show success message.
echo "Launcher: http://localhost:8080/launcher/"             # Show Launcher URL.
echo "Manager : http://127.0.0.1:9000/health"                # Show Manager API health URL.
