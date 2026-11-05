#!/usr/bin/env bash
# Shared configuration and helpers for StayNest's local lifecycle scripts.
#
# This file is sourced — never executed directly — by start_local.sh,
# stop_local.sh, health_local.sh, logs_local.sh, and check_local.sh.
#
# Configuration precedence:
#   1. variables already exported in the shell
#   2. .env.local at the repository root (gitignored, native script only)
#   3. defaults below
# Docker Compose reads a different file, .env (see .env.example), so the two
# workflows can coexist without overwriting each other's settings.

if [[ -z "${ROOT_DIR:-}" ]]; then
  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi
export ROOT_DIR

if [[ -f "$ROOT_DIR/.env.local" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env.local"
  set +a
fi

STATE_DIR="${STAYNEST_STATE_DIR:-$ROOT_DIR/.local}"
PGDATA="${STAYNEST_PGDATA:-$STATE_DIR/postgres-data}"
PGHOST="${STAYNEST_PGHOST:-127.0.0.1}"
PGPORT="${STAYNEST_PGPORT:-55432}"
PGUSER="${STAYNEST_PGUSER:-staynest}"
PGDATABASE="${STAYNEST_PGDATABASE:-staynest}"
API_HOST="${STAYNEST_API_HOST:-127.0.0.1}"
API_PORT="${STAYNEST_API_PORT:-8000}"
WEB_HOST="${STAYNEST_WEB_HOST:-127.0.0.1}"
WEB_PORT="${STAYNEST_WEB_PORT:-5173}"
API_URL="http://${API_HOST}:${API_PORT}"
WEB_URL="http://${WEB_HOST}:${WEB_PORT}"
LOGS_DIR="$STATE_DIR/logs"
RUN_DIR="$STATE_DIR/run"
VENV_DIR="${STAYNEST_VENV:-$ROOT_DIR/.venv}"
VENV_PY="$VENV_DIR/bin/python"
MIGRATIONS_DIR="$ROOT_DIR/backend/db/migrations"

# An explicitly provided database URL means "use that database and do not
# manage a project-local cluster". This is how CI or a shared dev server opts
# out of the bundled PostgreSQL instance.
if [[ -n "${STAYNEST_DB_URL:-}" ]]; then
  DB_MODE="external"
  DB_URL="$STAYNEST_DB_URL"
else
  DB_MODE="local"
  DB_URL="postgresql+psycopg://${PGUSER}@${PGHOST}:${PGPORT}/${PGDATABASE}"
fi

case "$DB_URL" in
  sqlite:*|sqlite+*) DB_KIND="sqlite" ;;
  postgres://*|postgresql://*|postgresql+*) DB_KIND="postgres" ;;
  *) DB_KIND="other" ;;
esac

if [[ -t 1 ]]; then
  C_RESET=$'\033[0m'
  C_INFO=$'\033[1;36m'
  C_OK=$'\033[1;32m'
  C_WARN=$'\033[1;33m'
  C_FAIL=$'\033[1;31m'
else
  C_RESET=""
  C_INFO=""
  C_OK=""
  C_WARN=""
  C_FAIL=""
fi

log()  { printf '%s[staynest]%s %s\n' "$C_INFO" "$C_RESET" "$*"; }
ok()   { printf '%s[  ok  ]%s %s\n' "$C_OK" "$C_RESET" "$*"; }
warn() { printf '%s[ warn ]%s %s\n' "$C_WARN" "$C_RESET" "$*" >&2; }
fail() { printf '%s[ fail ]%s %s\n' "$C_FAIL" "$C_RESET" "$*" >&2; }
die()  { fail "$*"; exit 1; }
section() { printf '\n%s== %s ==%s\n' "$C_INFO" "$*" "$C_RESET"; }

# Turn a SQLAlchemy URL into something psql understands by dropping the
# driver suffix: postgresql+psycopg://... -> postgresql://...
to_libpq_url() {
  printf '%s' "$1" | sed -E 's#^postgresql\+[A-Za-z0-9_]+://#postgresql://#'
}

port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
  elif command -v nc >/dev/null 2>&1; then
    nc -z 127.0.0.1 "$port" >/dev/null 2>&1
  else
    (exec 3<>"/dev/tcp/127.0.0.1/$port") >/dev/null 2>&1
  fi
}

port_owner() {
  local port="$1" pid
  command -v lsof >/dev/null 2>&1 || { printf 'unknown process'; return 0; }
  pid="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null | head -n 1)"
  if [[ -n "$pid" ]]; then
    ps -p "$pid" -o command= 2>/dev/null | sed 's/^ *//'
  else
    printf 'unknown process'
  fi
}

# Wait until a URL answers with a 2xx within a timeout. `pidfile`, when given,
# lets us stop early if the background process has already exited.
wait_for_http() {
  local url="$1" timeout="$2" label="$3" pidfile="${4:-}" i pid
  printf '  waiting for %s' "$label"
  for ((i = 0; i < timeout; i++)); do
    if curl -fsS --max-time 3 "$url" >/dev/null 2>&1; then
      printf ' ready\n'
      return 0
    fi
    if [[ -n "$pidfile" && -f "$pidfile" ]]; then
      pid="$(cat "$pidfile" 2>/dev/null || true)"
      if [[ -n "$pid" ]] && ! kill -0 "$pid" 2>/dev/null; then
        printf ' exited\n'
        return 1
      fi
    fi
    printf '.'
    sleep 1
  done
  printf ' timed out\n'
  return 1
}

# Find PostgreSQL client/server binaries. Homebrew on Apple Silicon, Homebrew
# on Intel, Postgres.app, and a normal PATH install are all supported.
resolve_pg_bin() {
  local candidate
  if command -v initdb >/dev/null 2>&1 \
    && command -v pg_ctl >/dev/null 2>&1 \
    && command -v psql >/dev/null 2>&1 \
    && command -v pg_isready >/dev/null 2>&1 \
    && command -v createdb >/dev/null 2>&1; then
    PG_BIN="$(cd "$(dirname "$(command -v initdb)")" && pwd)"
    return 0
  fi
  for candidate in \
    /opt/homebrew/opt/postgresql@*/bin \
    /usr/local/opt/postgresql@*/bin \
    /opt/homebrew/bin \
    /usr/local/bin \
    /Applications/Postgres.app/Contents/Versions/latest/bin; do
    if [[ -x "$candidate/initdb" && -x "$candidate/pg_ctl" && -x "$candidate/psql" \
      && -x "$candidate/pg_isready" && -x "$candidate/createdb" ]]; then
      PG_BIN="$candidate"
      return 0
    fi
  done
  return 1
}

postgres_install_hint() {
  cat >&2 <<'HINT'
PostgreSQL tools (initdb, pg_ctl, psql) were not found.
  macOS (Homebrew):  brew install postgresql@16 && brew link --force postgresql@16
  macOS (Postgres.app): install it and add
                        /Applications/Postgres.app/Contents/Versions/latest/bin to PATH
  Ubuntu/Debian:     sudo apt-get install postgresql postgresql-client
Then rerun ./scripts/start_local.sh, or point STAYNEST_DB_URL at an existing
database (see .env.local.example).
HINT
}

ensure_state_dirs() {
  mkdir -p "$STATE_DIR" "$LOGS_DIR" "$RUN_DIR"
}

# Print the comment header of a script (everything between the shebang and the
# first non-comment line), used by each script's --help.
print_help() {
  local file="$1" line
  while IFS= read -r line; do
    [[ "$line" == '#!'* ]] && continue
    [[ "$line" == '#'* ]] || break
    if [[ "$line" == "#" ]]; then
      printf '\n'
    else
      printf '%s\n' "${line#\# }"
    fi
  done < "$file"
}

is_staynest_api() {
  curl -fsS --max-time 3 "$1/health" 2>/dev/null | grep -q '"success"[[:space:]]*:[[:space:]]*true'
}

# True only when a PID file names a live numeric process.
pid_file_alive() {
  local pidfile="$1" pid
  [[ -s "$pidfile" ]] || return 1
  pid="$(cat "$pidfile" 2>/dev/null || true)"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" 2>/dev/null
}
