#!/usr/bin/env bash
# StayNest — local health check with actionable failures.
#
#   ./scripts/health_local.sh
#
# Checks, in dependency order:
#   PostgreSQL -> FastAPI /health -> search endpoint -> Vite -> Vite /api proxy
# It also reports persisted row counts so a silent in-memory fallback is visible.
# Exit code is 0 only when every check passes.
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
    die "Unknown argument: $1 (health_local.sh takes no arguments)"
    ;;
esac

PASS_COUNT=0
FAIL_COUNT=0

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  printf '%s[ pass ]%s %s\n' "$C_OK" "$C_RESET" "$*"
}

problem() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  printf '%s[ fail ]%s %s\n' "$C_FAIL" "$C_RESET" "$*"
}

note() { printf '         %s\n' "$*"; }

http_body() { curl -fsS --max-time 5 "$1" 2>/dev/null || true; }
http_code() { curl -sS -o /dev/null -w '%{http_code}' --max-time 5 "$1" 2>/dev/null || true; }

json_field() {
  local field="$1"
  python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('$field', ''))" 2>/dev/null || true
}

# ---------------------------------------------------------------------------
section "PostgreSQL"

if [[ "$DB_KIND" == "postgres" ]]; then
  PSQL_READY=0
  PG_UP=0
  if [[ "$DB_MODE" == "local" ]]; then
    if ! resolve_pg_bin; then
      problem "PostgreSQL tools not found"
      note "Install PostgreSQL (see RUNNING.md) or set STAYNEST_DB_URL."
    else
      PSQL_DB=("$PG_BIN/psql" -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -v ON_ERROR_STOP=1)
      PSQL_READY=1
      if "$PG_BIN/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; then
        if "$PG_BIN/pg_isready" -h "$PGHOST" -p "$PGPORT" -q; then
          PG_UP=1
          pass "PostgreSQL accepting connections at $PGHOST:$PGPORT"
        else
          problem "PostgreSQL process exists but is not accepting connections on $PGHOST:$PGPORT"
          note "Start: ./scripts/start_local.sh   Logs: ./scripts/logs_local.sh db"
        fi
      else
        problem "Project PostgreSQL is not running (${PGDATA#"$ROOT_DIR/"})"
        note "Start it with ./scripts/start_local.sh"
      fi
    fi
  else
    PSQL_DB=(psql "$(to_libpq_url "$DB_URL")" -v ON_ERROR_STOP=1)
    PSQL_READY=1
    if psql "$(to_libpq_url "$DB_URL")" -tAc "SELECT 1" >/dev/null 2>&1; then
      PG_UP=1
      pass "External PostgreSQL reachable"
    else
      problem "Cannot connect to STAYNEST_DB_URL"
      note "Verify host, port, database, credentials, and network access."
    fi
  fi

  if [[ "$PSQL_READY" == "1" && "$PG_UP" == "1" ]]; then
    counts="$("${PSQL_DB[@]}" -tA -F '|' -c \
      "SELECT (SELECT count(*) FROM users), (SELECT count(*) FROM listings), (SELECT count(*) FROM bookings), (SELECT count(*) FROM reviews)" 2>/dev/null || true)"
    if [[ -n "$counts" ]]; then
      IFS='|' read -r users listings bookings reviews <<< "$counts"
      approved="$("${PSQL_DB[@]}" -tAc "SELECT count(*) FROM listings WHERE status = 'APPROVED'" 2>/dev/null || true)"
      pending="$("${PSQL_DB[@]}" -tAc "SELECT count(*) FROM listings WHERE status = 'PENDING_APPROVAL'" 2>/dev/null || true)"
      pass "Schema present: users=$users listings=$listings (approved=$approved, pending=$pending) bookings=$bookings reviews=$reviews"
      if [[ "${users:-0}" == "0" || "${listings:-0}" == "0" ]]; then
        problem "Database is reachable but not seeded"
        note "Start the app once: ./scripts/start_local.sh"
      fi
    else
      problem "Tables are missing or unusable in the configured database"
      note "Run: ./scripts/start_local.sh (it applies backend/db/migrations/001_init.sql)"
    fi
  fi
elif [[ "$DB_KIND" == "sqlite" ]]; then
  if DB_URL="$DB_URL" ROOT_DIR="$ROOT_DIR" python3 - <<'PY' >/dev/null 2>&1
import os
import sqlite3
from urllib.parse import urlparse

url = os.environ["DB_URL"].split("?", 1)[0]
path = url.split("sqlite:///", 1)[1]
if not path.startswith("/"):
    path = os.path.join(os.environ["ROOT_DIR"], "backend", path)
conn = sqlite3.connect(path)
names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
raise SystemExit(0 if {"users", "listings", "bookings", "reviews"} <= names else 1)
PY
  then
    pass "SQLite schema present ($DB_URL)"
  else
    problem "SQLite database or tables are missing"
    note "Start the API once: ./scripts/start_local.sh"
  fi
else
  problem "Unsupported STAYNEST_DB_URL scheme: ${DB_URL%%://*}://"
fi

# ---------------------------------------------------------------------------
section "FastAPI"

api_code="$(http_code "$API_URL/health")"
if [[ "$api_code" == "200" ]]; then
  api_body="$(http_body "$API_URL/health")"
  if [[ "$(printf '%s' "$api_body" | json_field success)" == "True" ]]; then
    version="$(printf '%s' "$api_body" | python3 -c 'import json,sys; print((json.load(sys.stdin).get("data") or {}).get("version",""))' 2>/dev/null || true)"
    pass "API healthy at $API_URL/health${version:+ (version $version)}"
  else
    problem "API returned 200 but not the StayNest health envelope"
    note "Body: ${api_body:0:200}"
  fi
else
  problem "API is not healthy at $API_URL/health (HTTP ${api_code:-no response})"
  note "Start: ./scripts/start_local.sh   Logs: ./scripts/logs_local.sh api"
fi

search_body="$(http_body "$API_URL/listings/search?guests=2")"
search_count="$(printf '%s' "$search_body" | python3 -c 'import json,sys; d=json.load(sys.stdin); data=d.get("data") or []; print(len(data))' 2>/dev/null || true)"
if [[ -n "$search_count" ]]; then
  pass "Search endpoint returned $search_count approved listing(s) for guests=2"
  if [[ "$search_count" == "0" ]]; then
    note "Zero results can be valid; check the seed and approvals in the UI or /docs."
  fi
else
  problem "Search endpoint did not return a listing envelope"
  note "Try: curl '$API_URL/listings/search?guests=2'   Logs: ./scripts/logs_local.sh api"
fi

# ---------------------------------------------------------------------------
section "Vite"

web_code="$(http_code "$WEB_URL/")"
if [[ "$web_code" == "200" ]]; then
  pass "Web app responds at $WEB_URL"
else
  problem "Web app is not responding at $WEB_URL (HTTP ${web_code:-no response})"
  note "Start: ./scripts/start_local.sh   Logs: ./scripts/logs_local.sh web"
fi

proxy_body="$(http_body "$WEB_URL/api/health")"
proxy_ok="$(printf '%s' "$proxy_body" | json_field success)"
if [[ "$proxy_ok" == "True" ]]; then
  pass "Vite proxy /api -> $API_URL works"
else
  problem "Vite proxy /api is not reaching FastAPI"
  note "Restart Vite after config changes: ./scripts/stop_local.sh && ./scripts/start_local.sh"
  note "Check STAYNEST_API_URL (used by vite.config.js) and .local/logs/web.log."
fi

# ---------------------------------------------------------------------------
printf '\n'
if ((FAIL_COUNT == 0)); then
  ok "All checks passed — $PASS_COUNT passed, 0 failed"
  printf '  Web: %s\n  API: %s/docs\n' "$WEB_URL" "$API_URL"
  exit 0
fi

fail "$FAIL_COUNT check(s) failed, $PASS_COUNT passed"
printf '\nUseful commands:\n'
printf '  ./scripts/start_local.sh              start or repair the stack\n'
printf '  ./scripts/stop_local.sh               stop and keep data\n'
printf '  ./scripts/logs_local.sh [api|web|db]  inspect logs\n'
printf '  RUNNING.md                            full troubleshooting guide\n'
exit 1
