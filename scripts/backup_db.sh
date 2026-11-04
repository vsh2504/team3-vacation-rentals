#!/bin/bash
# Sprint 3, US31 — backup check (not a live Azure backup; run against your DB).
# Postgres: pg_dump "$DATABASE_URL" > "backup-$(date +%F).sql"
# SQLite:   cp staynest.db "backup-$(date +%F).db"
# Restore check: load the dump into a fresh DB and run the smoke test in scripts/load_test.py.
set -e
echo "Backup is a command, not a file in this repo. See the two commands above."
echo "DATABASE_URL set: ${DATABASE_URL:+yes}"
