# Scrum Journal — Sprint 3 (Weeks 6-7 scope, implemented 2026-11-04)

## Did
- Vinayak — Frontend deploy check in CI (npm ci + build); search health
  check is GET /listings/search in the load/acceptance scripts.
- Ranadhir — Azure Bicep template (VMSS min 2 + LB + Postgres + Blob +
  Key Vault + App Insights) — templates only, NOT provisioned, with a
  CI guard that fails if any `az deployment`/`az login` appears in CI.
- Manoj — DB: SQLAlchemy Core store (STAYNEST_DB_URL, SQLite verified,
  Postgres via docker-compose), migration 001_init.sql, backup script,
  parallel load test: 5 workers, exactly 1 success, 4 conflicts.
- Prajval — AnalyticsPage: host/admin dashboards, 30/60/90 + zip filter;
  analytics rentals = distinct listings (was bookings in Week 1).

## Doing next
- Sprint 4: demo script, final acceptance, README, tracker.

## Blocked
- Azure provisioning is blocked by design: it needs Vin's explicit
  approval for a specific paid deployment. No account was created.
  Local docker-compose is the verified deployment equivalent.
