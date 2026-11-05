#!/usr/bin/env bash
# Runs the role-based browser acceptance flow with the Playwright CLI.
set -Eeuo pipefail

FRONTEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_URL="${STAYNEST_ACCEPTANCE_URL:-http://127.0.0.1:4174}"
SCRIPT="tests/staynest-browser-acceptance.js"
case "${1:-}" in
  --live) SCRIPT="tests/staynest-live-smoke.js" ;;
  "") ;;
  *) printf 'Unknown argument: %s (use --live for the real-backend smoke)\n' "$1" >&2; exit 2 ;;
esac
SESSION="staynest-acceptance-$$"
DAEMON_DIR="$(mktemp -d "${TMPDIR:-/tmp}/staynest-playwright.XXXXXX")"
SERVER_PID=""

kill_tree() {
  local pid="$1" child
  for child in $(pgrep -P "$pid" 2>/dev/null || true); do
    kill_tree "$child"
  done
  kill "$pid" 2>/dev/null || true
}

cleanup() {
  PWTEST_DAEMON_SESSION_DIR="$DAEMON_DIR" playwright-cli -s="$SESSION" close >/dev/null 2>&1 || true
  if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    # npm spawns Vite as a grandchild, so killing only the background
    # subshell would leave the dev server bound to the acceptance port.
    kill_tree "$SERVER_PID"
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  rm -rf "$DAEMON_DIR"
}
trap cleanup EXIT

command -v playwright-cli >/dev/null 2>&1 || {
  printf 'playwright-cli is required. Install @playwright/cli, then rerun npm run test:browser.\n' >&2
  exit 1
}

if ! curl -fsS --max-time 2 "$BASE_URL" >/dev/null 2>&1; then
  if [[ "$BASE_URL" != "http://127.0.0.1:4174" ]]; then
    printf 'STAYNEST_ACCEPTANCE_URL is not reachable: %s\n' "$BASE_URL" >&2
    exit 1
  fi
  (
    cd "$FRONTEND_DIR"
    npm run dev -- --host 127.0.0.1 --port 4174 --strictPort
  ) >"$DAEMON_DIR/vite.log" 2>&1 &
  SERVER_PID=$!
  for _ in {1..30}; do
    curl -fsS --max-time 2 "$BASE_URL" >/dev/null 2>&1 && break
    kill -0 "$SERVER_PID" 2>/dev/null || {
      cat "$DAEMON_DIR/vite.log" >&2
      exit 1
    }
    sleep 1
  done
  curl -fsS --max-time 2 "$BASE_URL" >/dev/null 2>&1 || {
    printf 'Vite did not become ready at %s\n' "$BASE_URL" >&2
    cat "$DAEMON_DIR/vite.log" >&2
    exit 1
  }
fi

export STAYNEST_ACCEPTANCE_URL="$BASE_URL"
export PWTEST_DAEMON_SESSION_DIR="$DAEMON_DIR"
cd "$FRONTEND_DIR"
playwright-cli -s="$SESSION" open "$BASE_URL" --config .playwright/cli.config.json
playwright-cli -s="$SESSION" run-code --filename "$SCRIPT"
