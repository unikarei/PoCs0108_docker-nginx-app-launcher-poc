#!/bin/bash
# ------------------------------------------------------------------------------
# Purpose:
#   Validate that the Docker-based workflow is ready before starting or
#   stopping the container stack.
#
# What this script does:
#   - Checks that the docker command is present.
#   - Checks that docker compose is available.
#   - Verifies that the Docker daemon is reachable.
#   - Confirms the repository contains the Dockerfiles and compose file used
#     by the local container workflow.
#
# Notes:
#   - This is a readiness check only; it does not start containers.
#   - The next steps are run31_docker_start_dev.sh or run32_docker_start_prd.sh.
# ------------------------------------------------------------------------------
set -euo pipefail
SCRIPT_VERSION="v0.1.0"

cd "$(dirname "$0")"

printf '========================================\n'
printf '  YouTubeTranscripter Docker Init\n'
printf '========================================\n'
printf 'Script version : %s\n' "$SCRIPT_VERSION"
printf 'Project root   : %s\n' "$PWD"
printf '\n'

if ! command -v docker >/dev/null 2>&1; then
  echo "[Error] docker command not found in PATH." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "[Error] docker compose is not available." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "[Error] Docker daemon is not reachable." >&2
  echo "        Start Docker Desktop and retry." >&2
  exit 1
fi

if [ ! -f Dockerfile.api ]; then
  echo "[Error] Dockerfile.api not found." >&2
  exit 1
fi

if [ ! -f Dockerfile.worker ]; then
  echo "[Error] Dockerfile.worker not found." >&2
  exit 1
fi

if [ ! -f docker-compose.yml ]; then
  echo "[Error] docker-compose.yml not found." >&2
  exit 1
fi

echo "[OK] Docker daemon and compose files are ready."
echo "Next: run31_docker_start_dev.sh or run32_docker_start_prd.sh"
