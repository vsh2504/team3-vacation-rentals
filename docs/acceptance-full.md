# Full Product Acceptance Report

**Run date:** 2026-11-04 (America/Los_Angeles)

**Scope:** Task 4.2 — automated and role-based acceptance verification

**Worktree:** `conductor/d49b80f1-2330-4296-a125-d0edfcd2`

## Outcome

All automated checks passed in this run against a live local stack (PostgreSQL 18 on 127.0.0.1:55432, FastAPI on 8010, Vite on 5183, headless Chrome via Playwright CLI). The earlier sandbox-blocked state was resolved; nothing is reported as covered-but-unexecuted.

## Measured results

| Check | Command | Result |
|---|---|---|
| Backend + PostgreSQL acceptance | `STAYNEST_TEST_DB_URL=postgresql+psycopg://staynest@127.0.0.1:55432/staynest_acceptance .venv/bin/python -m pytest tests -q` (in `backend/`) | 66 passed, 0 skipped, 3 FastAPI/Starlette deprecation warnings |
| Browser acceptance (mocked API) | `cd frontend && npm run test:browser` | PASS, 10 areas (see below) |
| Live browser smoke | `STAYNEST_ACCEPTANCE_URL=http://127.0.0.1:5183 npm run test:browser:live` | PASS, 4 areas |
| Production build | `cd frontend && npm run build` | Passed; 630.70 kB JS (145.25 kB gzip), chunk-size warning only |
| Startup | `./scripts/start_local.sh` (ports 8010/5183) | Passed; users=5 listings=24 (20 approved, 4 pending) |
| Health | `./scripts/health_local.sh` | 6 passed, 0 failed |
| Restart persistence | `./scripts/stop_local.sh` then `start_local.sh` | Data preserved; counts identical; health 6/6 |

### PostgreSQL scenarios

1. Approved-only search, capacity, operating times, media/map fields, zero/negative/15-night rejection, exact 14-night acceptance.
2. Role enforcement, review rules, host/admin analytics scope, ZIP filter, invalid periods, cancellation and cancelled-booking exclusion.
3. Store reconstruction after writes (users, approval state, extended listing fields, booking snapshot, reviews).
4. Two simultaneous overlapping bookings: exactly one 200, one 409, one confirmed row.

### Browser areas (mocked API, 10)

Unavailable action and address geocoding; search and map interaction; booking; 375×812 mobile navigation without horizontal overflow; host listing management; host analytics; admin approval; admin analytics and ZIP filter; cancellation and cancelled tab; completed-stay review.

### Live smoke (real API, 4)

Search/detail/OpenStreetMap link; host My Listings; admin moderation and analytics; mobile layout. A regex bug in the smoke script (`listing(s) found`) was fixed to match the UI text "N listings found (API)".

## Reproduction

```text
./scripts/start_local.sh
createdb -h 127.0.0.1 -p 55432 -U staynest staynest_acceptance
cd backend && STAYNEST_TEST_DB_URL=postgresql+psycopg://staynest@127.0.0.1:55432/staynest_acceptance ../.venv/bin/python -m pytest tests -q
cd ../frontend && npm run test:browser && STAYNEST_ACCEPTANCE_URL=http://127.0.0.1:5173 npm run test:browser:live
cd .. && ./scripts/health_local.sh
```

The acceptance database is reset by the tests; it must be dedicated (name containing `test` or `acceptance`).

## External-provider boundaries

- Nominatim/Google geocoding selection and error handling are tested with deterministic provider doubles. No live address is transmitted during acceptance.
- Google address search requires a configured key; none is committed or available.
- OpenStreetMap tile uptime is not an application acceptance dependency; coordinates and OSM links are verified independently.
- No paid Azure resources or public deployment were created or tested in this task.

## Remaining acceptance risks

1. No automated contrast/accessibility engine; WCAG contrast is a manual audit item.
2. JS bundle exceeds 500 kB; code splitting is a performance follow-up.
3. Live Nominatim, Google address search and OSM tile availability were not exercised.
