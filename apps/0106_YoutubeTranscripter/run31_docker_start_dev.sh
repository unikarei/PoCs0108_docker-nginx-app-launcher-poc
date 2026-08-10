#!/bin/bash
# ------------------------------------------------------------------------------
# Purpose:
#   Start the Docker Compose stack in development mode and keep the logs in
#   the current terminal.
#
# What this script does:
#   - Checks that docker, docker compose, and the daemon are available.
#   - Runs docker compose up --build in the foreground.
#   - Uses the repository's docker-compose.yml and Dockerfiles to build the
#     backend and worker images before starting the stack.
#
# Notes:
#   - Use this when you want to see live container logs in the terminal.
#   - The companion detached launcher is run32_docker_start_prd.sh.
# ------------------------------------------------------------------------------
set -euo pipefail
SCRIPT_VERSION="v0.1.0"

cd "$(dirname "$0")"

printf '========================================\n'
printf '  YouTubeTranscripter Docker Compose (Dev)\n'
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

docker compose up --build
