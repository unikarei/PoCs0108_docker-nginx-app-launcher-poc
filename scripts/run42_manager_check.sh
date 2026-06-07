#!/usr/bin/env bash                                          # Use bash to run this script.
set -euo pipefail                                            # Stop on error, undefined variable, or pipe failure.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"                     # Project root is the parent folder of scripts.
cd "$ROOT"                                                   # Move to the project root.

echo "=========================================================" # Print title separator.
echo "[run42] Check host-side Manager API"                     # Print script purpose.
echo "=========================================================" # Print title separator.

# ------------------------------------------------------------ # Define helper function for one URL check.
check_url() {                                                 # Start URL check helper function.
  local url="$1"                                              # Read target URL from argument.
  if curl -fsS "$url" >/dev/null 2>&1; then                   # Request the URL and check success.
    echo "[OK] $url"                                          # Print successful URL.
  else                                                        # Handle failed request.
    echo "[ERROR] $url" >&2                                   # Print failed URL.
    return 1                                                  # Return failure from helper.
  fi                                                          # End curl result branch.
}                                                             # End URL check helper function.

check_url "http://127.0.0.1:9000/health"                      # Check Manager API health endpoint.
check_url "http://127.0.0.1:9000/api/status"                  # Check Manager API status endpoint.

echo                                                          # Print blank line.
echo "[OK] Manager API check finished."                        # Show success message.
