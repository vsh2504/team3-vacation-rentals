#!/usr/bin/env bash
# StayNest — stop the local development services.
#
#   ./scripts/stop_local.sh              stop Vite, FastAPI, and PostgreSQL
#   ./scripts/stop_local.sh --keep-db    stop Vite and FastAPI, leave PostgreSQL running
#
# The database directory and all rows are always preserved. This script never
# runs DROP DATABASE, deletes .local/postgres-data, or removes the Compose
# volume. Start again with ./scripts/start_local.sh whenever you are ready.
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib_local.sh
source "$ROOT_DIR/scripts/lib_local.sh"

KEEP_DB=0
for arg in "$@"; do
  case "$arg" in
    --keep-db) KEEP_DB=1 ;;
    -h|--help)
      print_help "$0"
      exit 0
      ;;
    *)
      fail "Unknown option: $arg"
      printf 'Usage: %s [--keep-db]\n' "$0" >&2
      exit 2
      ;;
  esac
done

ensure_state_dirs

stop_pidfile() {
  local service="$1" pidfile="$2" pid child i
  if [[ ! -f "$pidfile" ]]; then
    return 0
  fi
  pid="$(cat "$pidfile" 2>/dev/null || true)"
  if [[ -z "$pid" ]] || ! kill -0 "$pid" 2>/dev/null; then
    rm -f "$pidfile"
    log "$service is not running (stale pid file removed)"
    return 0
  fi
  log "Stopping $service (pid $pid)"
  # npm/uvicorn may have a child process; stop children first.
  children="$(pgrep -P "$pid" 2>/dev/null || true)"
  for child in $children; do
    kill -TERM "$child" 2>/dev/null || true
  done
  kill -TERM "$pid" 2>/dev/null || true
  for ((i = 0; i < 20; i++)); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.5
  done
  if kill -0 "$pid" 2>/dev/null; then
    warn "$service did not exit after 10s; sending SIGKILL"
    kill -KILL "$pid" 2>/dev/null || true
  fi
  rm -f "$pidfile"
  ok "$service stopped"
}

# If a PID file was lost, only stop obvious StayNest processes on our ports.
stop_orphan_listener() {
  local port="$1" label="$2" pid cmd
  command -v lsof >/dev/null 2>&1 || return 0
  for pid in $(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true); do
    cmd="$(ps -p "$pid" -o command= 2>/dev/null | sed 's/^ *//')"
    case "$cmd" in
      *"$ROOT_DIR"*vite*|*"$ROOT_DIR"*uvicorn*)
        warn "$label still listening on port $port (pid $pid); stopping it"
        kill -TERM "$pid" 2>/dev/null || true
        sleep 1
        kill -0 "$pid" 2>/dev/null && kill -KILL "$pid" 2>/dev/null || true
        ;;
      "")
        ;;
      *)
        warn "Port $port is used by another process and was left alone: $cmd"
        ;;
    esac
  done
}

section "Stopping StayNest"
stop_pidfile "Vite" "$RUN_DIR/web.pid"
stop_orphan_listener "$WEB_PORT" "Vite"

stop_pidfile "FastAPI" "$RUN_DIR/api.pid"
stop_orphan_listener "$API_PORT" "FastAPI"

if [[ "$KEEP_DB" == "1" ]]; then
  log "Leaving PostgreSQL running (--keep-db)"
elif [[ "$DB_MODE" == "external" ]]; then
  log "External database configured; this script does not stop it"
elif [[ -s "$PGDATA/PG_VERSION" ]] && resolve_pg_bin && "$PG_BIN/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; then
  log "Stopping PostgreSQL at $PGHOST:$PGPORT"
  if "$PG_BIN/pg_ctl" -D "$PGDATA" -m fast -w -t 30 stop >/dev/null; then
    ok "PostgreSQL stopped"
  else
    warn "PostgreSQL did not stop cleanly — see .local/logs/postgres.log"
  fi
else
  log "Project PostgreSQL is not running"
fi

printf '\n'
if [[ "$DB_MODE" == "local" && -d "$PGDATA" ]]; then
  ok "Data preserved in ${PGDATA#"$ROOT_DIR/"} — restart with ./scripts/start_local.sh"
else
  ok "Restart with ./scripts/start_local.sh"
fi
