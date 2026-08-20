#!/usr/bin/env bash                                          # Use bash to run this script.
set -euo pipefail                                            # Stop on error, undefined variable, or pipe failure.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"                   # Project root is the parent folder of scripts.
cd "$ROOT"                                                   # Move to the project root.

STAMP="$(date +%Y%m%d-%H%M%S)"                               # Create a sortable backup timestamp.
mkdir -p backups                                              # Create the local backup directory.
REMOTE=/tmp/youtube-transcription-backup.dump                 # Use a container-side binary file to avoid text encoding.
LOCAL="backups/youtube-transcription-${STAMP}.dump"           # Choose the local backup path.

docker compose -f database/docker-compose.yml exec -T youtube-db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom -f /tmp/youtube-transcription-backup.dump' # Create a custom-format dump inside the DB container.
docker compose -f database/docker-compose.yml cp "youtube-db:${REMOTE}" "$LOCAL" # Copy the binary dump to the host.
docker compose -f database/docker-compose.yml exec -T youtube-db rm -f "$REMOTE" >/dev/null # Remove only the temporary container file.
echo "[OK] Database backup created: $LOCAL"                    # Show the backup path.
