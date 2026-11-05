#!/usr/bin/env bash
# StayNest — read local service logs without hunting through the repo.
#
#   ./scripts/logs_local.sh            last 200 lines of each log
#   ./scripts/logs_local.sh api        last 200 lines of the API log
#   ./scripts/logs_local.sh web -f     follow the Vite log
#   ./scripts/logs_local.sh db -n 50   last 50 lines of PostgreSQL
#
# Targets: api | web | db | postgres | all (default)
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib_local.sh
source "$ROOT_DIR/scripts/lib_local.sh"

target="all"
lines=200
follow=0

while (($# > 0)); do
  case "$1" in
    api|web|db|postgres|all)
      target="$1"
      shift
      ;;
    -f|--follow)
      follow=1
      shift
      ;;
    -n|--lines)
      [[ $# -ge 2 ]] || die "-n/--lines requires a number"
      lines="$2"
      shift 2
      ;;
    -h|--help)
      print_help "$0"
      exit 0
      ;;
    *)
      die "Unknown argument: $1 (expected api|web|db|all, -f, or -n <lines>)"
      ;;
  esac
done

[[ "$lines" =~ ^[0-9]+$ ]] || die "--lines must be a positive number"

tail_one() {
  local label="$1" file="$2"
  printf '\n%s== %s (%s) ==%s\n' "$C_INFO" "$label" "${file#"$ROOT_DIR/"}" "$C_RESET"
  if [[ ! -f "$file" ]]; then
    printf '  (no log yet — has the service started? Run ./scripts/start_local.sh)\n'
    return 0
  fi
  if [[ "$follow" == "1" ]]; then
    tail -n "$lines" -f "$file"
  else
    tail -n "$lines" "$file"
  fi
}

case "$target" in
  api) tail_one "FastAPI" "$LOGS_DIR/api.log" ;;
  web) tail_one "Vite" "$LOGS_DIR/web.log" ;;
  db|postgres)
    tail_one "PostgreSQL" "$LOGS_DIR/postgres.log"
    tail_one "initdb" "$LOGS_DIR/initdb.log"
    ;;
  all)
    tail_one "FastAPI" "$LOGS_DIR/api.log"
    [[ "$follow" == "1" ]] && exit 0
    tail_one "Vite" "$LOGS_DIR/web.log"
    tail_one "PostgreSQL" "$LOGS_DIR/postgres.log"
    ;;
esac
