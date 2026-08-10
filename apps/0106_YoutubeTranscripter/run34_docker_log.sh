#!/bin/bash
# ------------------------------------------------------------------------------
# Purpose:
#   Stream Docker Compose logs for the repository's container stack.
#
# What this script does:
#   - Checks that docker and docker compose are available.
#   - Runs docker compose logs -f so the terminal follows container output.
#
# Notes:
#   - This is useful after a detached launch from run32_docker_start_prd.sh.
#   - Use Ctrl+C to stop following the log stream.
# ------------------------------------------------------------------------------
set -euo pipefail
SCRIPT_VERSION="v0.1.0"

cd "$(dirname "$0")"

printf '========================================\n'
printf '  YouTubeTranscripter Docker Compose Logs\n'
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

docker compose logs -f
