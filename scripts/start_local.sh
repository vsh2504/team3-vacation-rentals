#!/usr/bin/env bash
# StayNest — one-command local development environment.
#
#   ./scripts/start_local.sh
#
# What it does, in order:
#   1. validates Python 3.10+, Node 18+, npm, curl, and PostgreSQL tools
#   2. creates/updates .venv and frontend/node_modules as needed
#   3. starts a project-local PostgreSQL cluster (default 127.0.0.1:55432)
#   4. applies backend/db/migrations/001_init.sql
#   5. runs the deterministic development seed (only when the database is empty)
#   6. starts FastAPI on 127.0.0.1:8000 and Vite on 127.0.0.1:5173
#   7. waits for readiness and prints URLs, health commands, and demo logins
#
# Re-running this script is safe. It reuses services that are already up and
# never drops a database, deletes a volume, or overwrites existing rows.
# Data survives restarts. To point at your own database instead, export
# STAYNEST_DB_URL (see .env.local.example).
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib_local.sh
source "$ROOT_DIR/scripts/lib_local.sh"

case "${1:-}" in
  -h|--help)
    print_help "$0"
    exit 0
    ;;
  "")
    ;;
  *)
    die "Unknown argument: $1 (start_local.sh takes no arguments; use .env.local for options)"
    ;;
esac

# ---------------------------------------------------------------------------
# Failure reporting: print the tail of the relevant logs once, then exit.
# ---------------------------------------------------------------------------
on_exit() {
  local code=$?
  if ((code != 0)); then
    printf '\n'
    warn "Startup did not complete (exit $code)."
    local file
    for file in "$LOGS_DIR/api.log" "$LOGS_DIR/web.log" "$LOGS_DIR/postgres.log"; do
      if [[ -s "$file" ]]; then
        printf '\n--- last 20 lines of %s ---\n' "${file#"$ROOT_DIR/"}"
        tail -n 20 "$file" || true
      fi
    done
    printf '\nNext steps:\n'
    printf '  ./scripts/logs_local.sh          # full logs\n'
    printf '  ./scripts/health_local.sh        # service-by-service diagnosis\n'
    printf '  ./scripts/stop_local.sh          # stop anything already running\n'
    printf '  RUNNING.md                       # prerequisites and troubleshooting\n'
  fi
}
trap on_exit EXIT

# ---------------------------------------------------------------------------
# Prerequisite validation
# ---------------------------------------------------------------------------
section "Checking prerequisites"

missing=()
for tool in python3 node npm curl; do
  command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
done

bad_versions=()
if command -v python3 >/dev/null 2>&1; then
  if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    bad_versions+=("Python 3.10+ is required (found $(python3 --version 2>&1))")
  fi
fi
if command -v node >/dev/null 2>&1; then
  if ! node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 18 ? 0 : 1)' >/dev/null 2>&1; then
    bad_versions+=("Node 18+ is required (found $(node --version 2>&1))")
  fi
fi

if [[ "$DB_KIND" == "postgres" ]]; then
  if [[ "$DB_MODE" == "local" ]]; then
    if ! resolve_pg_bin; then
      postgres_install_hint
      missing+=("postgresql (initdb/pg_ctl/psql)")
    fi
  elif ! command -v psql >/dev/null 2>&1; then
    postgres_install_hint
    missing+=("psql (needed to apply migrations to STAYNEST_DB_URL)")
  fi
fi

if (( ${#missing[@]} > 0 )); then
  fail "Missing required tools: ${missing[*]}"
  printf 'Install the tools above and rerun ./scripts/start_local.sh\n' >&2
  printf 'Or run with STAYNEST_DB_URL=sqlite:///./staynest.db to use SQLite instead.\n' >&2
  exit 1
fi
if (( ${#bad_versions[@]} > 0 )); then
  fail "Unsupported runtime version:"
  printf '  - %s\n' "${bad_versions[@]}" >&2
  exit 1
fi
ok "Python $(python3 -c 'import platform; print(platform.python_version())'), Node $(node --version), npm $(npm --version)"
if [[ "$DB_MODE" == "local" ]]; then
  ok "PostgreSQL tools: $PG_BIN"
else
  ok "External database configured: $DB_KIND (${DB_URL%%://*}://…)"
fi

ensure_state_dirs

# ---------------------------------------------------------------------------
# Dependencies (idempotent; only reinstalled when manifests change)
# ---------------------------------------------------------------------------
hash_file() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    sha256sum "$1" | awk '{print $1}'
  fi
}

hash_stdin() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 | awk '{print $1}'
  else
    sha256sum | awk '{print $1}'
  fi
}

section "Python environment"
if [[ ! -x "$VENV_PY" ]]; then
  log "Creating virtualenv at ${VENV_DIR#"$ROOT_DIR/"}"
  python3 -m venv "$VENV_DIR"
fi
REQ_HASH="$(hash_file "$ROOT_DIR/backend/requirements.txt")"
REQ_STAMP="$STATE_DIR/requirements.sha256"
if [[ ! -f "$REQ_STAMP" || "$(cat "$REQ_STAMP")" != "$REQ_HASH" ]]; then
  log "Installing backend dependencies (first run only, ~1 minute)"
  "$VENV_PY" -m pip install --quiet --disable-pip-version-check --upgrade pip
  "$VENV_PY" -m pip install --quiet --disable-pip-version-check -r "$ROOT_DIR/backend/requirements.txt"
  printf '%s' "$REQ_HASH" > "$REQ_STAMP"
  ok "Backend dependencies installed"
else
  ok "Backend dependencies up to date"
fi

section "Frontend environment"
NPM_STAMP="$STATE_DIR/npm.sha256"
NPM_HASH="$(cat "$ROOT_DIR/frontend/package.json" "$ROOT_DIR/frontend/package-lock.json" 2>/dev/null | hash_stdin)"
if [[ ! -d "$ROOT_DIR/frontend/node_modules" || ! -f "$NPM_STAMP" || "$(cat "$NPM_STAMP")" != "$NPM_HASH" ]]; then
  log "Installing frontend dependencies"
  if [[ -f "$ROOT_DIR/frontend/package-lock.json" ]]; then
    (cd "$ROOT_DIR/frontend" && npm ci --no-audit --no-fund)
  else
    (cd "$ROOT_DIR/frontend" && npm install --no-audit --no-fund)
  fi
  printf '%s' "$NPM_HASH" > "$NPM_STAMP"
  ok "Frontend dependencies installed"
else
  ok "Frontend dependencies up to date"
fi

# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------
write_pg_config() {
  cat > "$PGDATA/staynest-local.conf" <<EOF
# Managed by scripts/start_local.sh. Local development only.
# Unix sockets intentionally use PostgreSQL's short default (usually /tmp):
# repository paths can exceed the 103-byte socket path limit.
port = $PGPORT
listen_addresses = '$PGHOST'
EOF
  if ! grep -q "staynest-local.conf" "$PGDATA/postgresql.conf"; then
    {
      printf '\n# StayNest local development overrides\n'
      printf "include_if_exists = 'staynest-local.conf'\n"
    } >> "$PGDATA/postgresql.conf"
  fi
}

start_local_postgres() {
  section "PostgreSQL"
  if [[ ! "$PGUSER" =~ ^[A-Za-z_][A-Za-z0-9_]*$ || ! "$PGDATABASE" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    die "STAYNEST_PGUSER and STAYNEST_PGDATABASE must be simple identifiers (letters, digits, underscore)."
  fi
  if [[ "$PGHOST" != "127.0.0.1" && "$PGHOST" != "localhost" && "$PGHOST" != "::1" ]]; then
    warn "Project PostgreSQL uses trust authentication; listening on $PGHOST exposes it beyond this machine. Keep PGHOST on loopback."
  fi

  local already_running=0
  if [[ -s "$PGDATA/PG_VERSION" ]] && "$PG_BIN/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; then
    local active_port
    active_port="$(sed -n '4p' "$PGDATA/postmaster.pid" 2>/dev/null || true)"
    if [[ "$active_port" != "$PGPORT" ]]; then
      die "Project PostgreSQL is already running on port ${active_port:-unknown}, but STAYNEST_PGPORT=$PGPORT. Run ./scripts/stop_local.sh, then start again."
    fi
    already_running=1
    ok "PostgreSQL already running at $PGHOST:$PGPORT (data: ${PGDATA#"$ROOT_DIR/"})"
  fi

  if ((already_running == 0)); then
    if port_in_use "$PGPORT"; then
      die "Port $PGPORT is already in use by: $(port_owner "$PGPORT"). Set STAYNEST_PGPORT to another port (for example 55433) or stop that process."
    fi

    if [[ ! -s "$PGDATA/PG_VERSION" ]]; then
      if [[ -d "$PGDATA" && -n "$(ls -A "$PGDATA" 2>/dev/null)" ]]; then
        die "$PGDATA exists but is not a PostgreSQL cluster. Move it aside or set STAYNEST_PGDATA to a new path."
      fi
      mkdir -p "$PGDATA"
      chmod 700 "$PGDATA"
      log "Initializing project-local PostgreSQL cluster in ${PGDATA#"$ROOT_DIR/"}"
      if ! "$PG_BIN/initdb" -D "$PGDATA" -U "$PGUSER" \
        --auth-local=trust --auth-host=trust --encoding=UTF8 \
        >"$LOGS_DIR/initdb.log" 2>&1; then
        die "initdb failed — see ${LOGS_DIR#"$ROOT_DIR/"}/initdb.log"
      fi
      ok "Cluster initialized (superuser: $PGUSER, loopback trust auth, development only)"
    else
      ok "Reusing existing cluster at ${PGDATA#"$ROOT_DIR/"}"
    fi

    write_pg_config
    log "Starting PostgreSQL on $PGHOST:$PGPORT"
    if ! "$PG_BIN/pg_ctl" -D "$PGDATA" -l "$LOGS_DIR/postgres.log" -w -t 60 start >/dev/null; then
      die "PostgreSQL did not start — see ${LOGS_DIR#"$ROOT_DIR/"}/postgres.log"
    fi
  fi

  local i
  for ((i = 0; i < 30; i++)); do
    if "$PG_BIN/pg_isready" -h "$PGHOST" -p "$PGPORT" -q; then break; fi
    sleep 1
  done
  "$PG_BIN/pg_isready" -h "$PGHOST" -p "$PGPORT" >/dev/null \
    || die "PostgreSQL process started but is not accepting connections on $PGHOST:$PGPORT — see .local/logs/postgres.log"

  local exists
  exists="$("$PG_BIN/psql" -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname = '$PGDATABASE'")"
  if [[ "$exists" != "1" ]]; then
    log "Creating database $PGDATABASE"
    "$PG_BIN/createdb" -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$PGDATABASE"
  fi
  ok "PostgreSQL ready at $PGHOST:$PGPORT (database: $PGDATABASE)"
}

check_external_postgres() {
  section "PostgreSQL (external)"
  local libpq
  libpq="$(to_libpq_url "$DB_URL")"
  if ! psql "$libpq" -v ON_ERROR_STOP=1 -tAc "SELECT 1" >/dev/null 2>&1; then
    die "Cannot connect to STAYNEST_DB_URL. Check host, port, database, and credentials, then rerun."
  fi
  ok "Connected to external PostgreSQL"
}

if [[ "$DB_MODE" == "local" ]]; then
  start_local_postgres
elif [[ "$DB_KIND" == "postgres" ]]; then
  check_external_postgres
elif [[ "$DB_KIND" == "sqlite" ]]; then
  section "SQLite (external)"
  warn "SQLite mode: schema creation and seeding are handled by the API startup path."
else
  warn "Unrecognised STAYNEST_DB_URL scheme; schema creation is left to the API."
fi

# psql command used for migrations, counts, and health checks.
build_psql_commands() {
  if [[ "$DB_MODE" == "local" ]]; then
    PSQL_DB=("$PG_BIN/psql" -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -v ON_ERROR_STOP=1)
  else
    PSQL_DB=(psql "$(to_libpq_url "$DB_URL")" -v ON_ERROR_STOP=1)
  fi
}

# ---------------------------------------------------------------------------
# Migrations + deterministic development seed
# ---------------------------------------------------------------------------
section "Schema and development data"
if [[ "$DB_KIND" == "postgres" ]]; then
  build_psql_commands
  log "Applying backend/db/migrations/001_init.sql (idempotent; existing rows are untouched)"
  "${PSQL_DB[@]}" -q -f "$MIGRATIONS_DIR/001_init.sql" >/dev/null
  ok "Migration applied"
fi

log "Initializing the store (creates missing tables and seeds only when empty)"
SEED_SUMMARY="$(cd "$ROOT_DIR/backend" && STAYNEST_DB_URL="$DB_URL" "$VENV_PY" - <<'PY'
from app.db import make_store

store = make_store()
if store is None:
    raise SystemExit("STAYNEST_DB_URL was not visible to the application")
print(
    f"users={len(store.users)} "
    f"listings={len(store.listings)} "
    f"bookings={len(store.bookings)} "
    f"reviews={len(store.reviews)}"
)
PY
)" || die "Could not initialize the database. Check the URL and PostgreSQL logs."
SEED_SUMMARY="$(printf '%s\n' "$SEED_SUMMARY" | tail -n 1)"
ok "Database ready ($SEED_SUMMARY)"

# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------
section "FastAPI"

start_api() {
  local pidfile="$RUN_DIR/api.pid"
  if is_staynest_api "$API_URL"; then
    if pid_file_alive "$pidfile"; then
      ok "API already running at $API_URL (pid $(cat "$pidfile"))"
      return 0
    fi
    die "Something is already answering $API_URL/health, but this script did not start it. Stop that process (see: lsof -nP -iTCP:$API_PORT -sTCP:LISTEN) or set STAYNEST_API_PORT to another port."
  fi
  if port_in_use "$API_PORT"; then
    die "Port $API_PORT is already in use by: $(port_owner "$API_PORT"). Set STAYNEST_API_PORT to another port."
  fi

  log "Starting FastAPI on $API_URL"
  local reload_args=()
  if [[ "${STAYNEST_RELOAD:-0}" == "1" ]]; then
    reload_args=(--reload --reload-dir app)
    log "Hot reload enabled (STAYNEST_RELOAD=1)"
  fi
  (
    cd "$ROOT_DIR/backend"
    export STAYNEST_DB_URL="$DB_URL"
    export JWT_SECRET="${JWT_SECRET:-dev-only-change-in-azure-key-vault}"
    nohup "$VENV_PY" -m uvicorn app.main:app \
      --host "$API_HOST" --port "$API_PORT" \
      ${reload_args[@]+"${reload_args[@]}"} \
      >"$LOGS_DIR/api.log" 2>&1 &
    echo $! > "$pidfile"
  )

  if ! wait_for_http "$API_URL/health" 60 "API" "$pidfile"; then
    die "FastAPI did not become healthy within 60s — see .local/logs/api.log"
  fi
  ok "API healthy at $API_URL/health (docs: $API_URL/docs)"
}

start_api

# ---------------------------------------------------------------------------
# Vite
# ---------------------------------------------------------------------------
section "Vite"

start_web() {
  local pidfile="$RUN_DIR/web.pid"
  if curl -fsS --max-time 3 "$WEB_URL/" >/dev/null 2>&1; then
    if pid_file_alive "$pidfile"; then
      ok "Vite already running at $WEB_URL (pid $(cat "$pidfile"))"
      return 0
    fi
    die "Something is already answering $WEB_URL, but this script did not start it. Stop that process (see: lsof -nP -iTCP:$WEB_PORT -sTCP:LISTEN) or set STAYNEST_WEB_PORT to another port."
  fi
  if port_in_use "$WEB_PORT"; then
    die "Port $WEB_PORT is already in use by: $(port_owner "$WEB_PORT"). Set STAYNEST_WEB_PORT to another port."
  fi

  log "Starting Vite on $WEB_URL (proxying /api -> $API_URL)"
  (
    cd "$ROOT_DIR/frontend"
    # vite.config.js reads this and forwards /api to the running API.
    export STAYNEST_API_URL="$API_URL"
    nohup npm run dev -- --host "$WEB_HOST" --port "$WEB_PORT" --strictPort \
      >"$LOGS_DIR/web.log" 2>&1 &
    echo $! > "$pidfile"
  )

  if ! wait_for_http "$WEB_URL/" 90 "Vite" "$pidfile"; then
    die "Vite did not become ready within 90s — see .local/logs/web.log"
  fi
  ok "Web app serving at $WEB_URL"
}

start_web

# Verify the proxy end-to-end; a mismatch here is the classic blank-page cause.
if curl -fsS --max-time 5 "$WEB_URL/api/health" 2>/dev/null | grep -q '"success"[[:space:]]*:[[:space:]]*true'; then
  ok "Vite proxy /api -> FastAPI verified"
else
  warn "Vite is up but $WEB_URL/api/health did not return the API envelope."
  warn "If the UI cannot load data, run ./scripts/health_local.sh and check .local/logs/web.log."
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
safe_db_url() {
  printf '%s' "$DB_URL" | sed -E 's#(://[^:/@]+:)[^@]*@#\1***@#'
}

section "StayNest is ready"
printf '  Web app       %s\n' "$WEB_URL"
printf '  API           %s\n' "$API_URL"
printf '  API health    %s/health\n' "$API_URL"
printf '  API docs      %s\n' "$API_URL/docs"
printf '  PostgreSQL    %s\n' "$(safe_db_url)"
if [[ "$DB_MODE" == "local" ]]; then
  printf '  Database data %s (survives restarts)\n' "${PGDATA#"$ROOT_DIR/"}"
else
  printf '  Database mode external (this script will not stop it)\n'
fi
printf '  Data          %s\n' "$SEED_SUMMARY"
printf '\n'
printf '  Health check  ./scripts/health_local.sh\n'
printf '  Logs          ./scripts/logs_local.sh [api|web|db|all]\n'
printf '  Stop          ./scripts/stop_local.sh          (keeps all data)\n'
printf '\n'
printf '  Demo logins   admin@staynest.local / admin12345\n'
printf '                host1@staynest.local / password123\n'
printf '                customer@staynest.local / password123\n'
printf '\n'
printf '  Re-run ./scripts/start_local.sh any time; running services are reused.\n'
