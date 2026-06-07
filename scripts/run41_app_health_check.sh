#!/usr/bin/env bash                                          # Use bash to run this script.
set -euo pipefail                                            # Stop on error, undefined variable, or pipe failure.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"                     # Project root is the parent folder of scripts.
cd "$ROOT"                                                   # Move to the project root.

echo "=========================================================" # Print title separator.
echo "[run41] Check application health endpoints"              # Print script purpose.
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

check_url "http://localhost:8080/launcher/health"             # Check Launcher health endpoint.
check_url "http://localhost:8080/app1/health"                 # Check App1 health endpoint.
check_url "http://localhost:8080/app2/health"                 # Check App2 health endpoint.
check_url "http://localhost:8080/app3/health"                 # Check App3 health endpoint.
check_url "http://localhost:8080/app4/health"                 # Check App4 health endpoint.

echo                                                          # Print blank line.
echo "[OK] Application health check finished."                 # Show success message.
