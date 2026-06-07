#!/usr/bin/env bash                                          # Use bash to run this script.
set -euo pipefail                                            # Stop on error, undefined variable, or pipe failure.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"                     # Project root is the parent folder of scripts.
LAUNCHER_BASIC_AUTH_USER="${LAUNCHER_BASIC_AUTH_USER:-launcher}" # Default Launcher username.
LAUNCHER_BASIC_AUTH_PASSWORD="${LAUNCHER_BASIC_AUTH_PASSWORD:-launcher-pass}" # Default Launcher password.
LAUNCHER_AUTH="${LAUNCHER_BASIC_AUTH_USER}:${LAUNCHER_BASIC_AUTH_PASSWORD}"    # Build user:password pair for curl.
cd "$ROOT"                                                   # Move to the project root.

echo "=========================================================" # Print title separator.
echo "[run40] Check Nginx reverse proxy routes"                # Print script purpose.
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

check_url_basic() {                                           # Start URL check helper with Basic auth.
  local url="$1"                                             # Read target URL from argument.
  if curl -fsS -u "$LAUNCHER_AUTH" "$url" >/dev/null 2>&1; then # Request URL with Basic auth.
    echo "[OK] $url"                                         # Print successful URL.
  else                                                        # Handle failed request.
    echo "[ERROR] $url" >&2                                  # Print failed URL.
    return 1                                                  # Return failure from helper.
  fi                                                          # End curl result branch.
}                                                             # End URL check helper function.

check_url_basic "http://localhost:8080/launcher/"             # Check Launcher route through Nginx with Basic auth.
check_url "http://localhost:8080/app1/"                       # Check App1 route through Nginx.
check_url "http://localhost:8080/app2/"                       # Check App2 route through Nginx.
check_url "http://localhost:8080/app3/"                       # Check App3 route through Nginx.
check_url "http://localhost:8080/app4/"                       # Check App4 route through Nginx.

echo                                                          # Print blank line.
echo "[OK] Nginx route check finished."                        # Show success message.
