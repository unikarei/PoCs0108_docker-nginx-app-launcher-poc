#!/bin/bash
# ------------------------------------------------------------------------------
# Purpose:
#   Start the Docker Compose stack in detached mode.
#
# What this script does:
#   - Checks that docker, docker compose, and the daemon are available.
#   - Runs docker compose up --build -d so the stack continues in the
#     background after the terminal returns.
#   - Uses the repository's docker-compose.yml and Dockerfiles to build the
#     backend and worker images before starting the stack.
#
# Notes:
#   - Use this when you want the containers to keep running after launch.
#   - This script does not switch compose to a separate production profile; it
#     uses the repository's current docker-compose.yml as-is.
#   - Follow with run34_docker_log.sh if you want to tail logs later.
# ------------------------------------------------------------------------------
set -euo pipefail
SCRIPT_VERSION="v0.1.0"

cd "$(dirname "$0")"

printf '========================================\n'
printf '  YouTubeTranscripter Docker Compose (Detached)\n'
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

docker compose up --build -d
