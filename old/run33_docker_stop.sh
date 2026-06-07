#!/bin/bash
# ------------------------------------------------------------------------------
# Purpose:
#   Stop and remove the Docker Compose stack for this repository.
#
# What this script does:
#   - Checks that docker and docker compose are available.
#   - Runs docker compose down to stop and remove the containers created by
#     the compose workflow.
#
# Notes:
#   - This script only targets the Docker Compose stack.
#   - It does not manage the optional local frontend PID file used by stop_app.sh.
# ------------------------------------------------------------------------------
set -euo pipefail
SCRIPT_VERSION="v0.1.0"

cd "$(dirname "$0")"

printf '========================================\n'
printf '  YouTubeTranscripter Docker Compose Stop\n'
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

docker compose down
