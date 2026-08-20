#!/usr/bin/env bash                                          # Use bash to run this script.
set -euo pipefail                                            # Stop on error, undefined variable, or pipe failure.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"                   # Project root is the parent folder of scripts.
cd "$ROOT"                                                   # Move to the project root.

if [[ $# -ne 1 || ! -f "$1" ]]; then                        # Require one existing custom-format dump.
  echo "Usage: run29_database_restore.sh path-to-dump" >&2    # Explain required input.
  exit 1                                                      # Exit with usage error.
fi
read -r -p "Type RESTORE to replace the external DB from $1: " CONFIRM # Require deliberate confirmation.
[[ "$CONFIRM" == "RESTORE" ]] || {                          # Abort unless the exact confirmation was entered.
  echo "[CANCELLED] Database restore was not confirmed."       # Explain the safe abort.
  exit 1                                                      # Exit with cancellation.
}

REMOTE=/tmp/youtube-transcription-restore.dump                 # Use a container-side binary file.
docker compose -f database/docker-compose.yml cp "$1" "youtube-db:${REMOTE}" # Copy the selected dump to the DB container.
docker compose -f database/docker-compose.yml exec -T youtube-db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner /tmp/youtube-transcription-restore.dump' # Restore only after explicit confirmation.
docker compose -f database/docker-compose.yml exec -T youtube-db rm -f "$REMOTE" >/dev/null # Remove only the temporary container file.
echo "[OK] Database restore completed."                        # Show success message.
