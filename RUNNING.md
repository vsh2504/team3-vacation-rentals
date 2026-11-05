# Running StayNest locally — see it working

## Option A (verified, no Docker needed) — recommended

Prerequisites: Python 3.12, Node 20+.

```bash
git clone https://github.com/vsh2504/team3-vacation-rentals.git
cd team3-vacation-rentals

# 1. API (terminal 1)
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload --port 8000
```

Open in your browser:
- API health: http://localhost:8000/health
- Swagger UI (click any endpoint -> Try it out): http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json

```bash
# 2. Web UI (terminal 2, from repo root)
cd frontend
npm install
npm run dev
```

Open: http://localhost:5173
Week 1 web UI is a scaffold: role nav (Customer/Host/Admin), search
with seed data, ListingCard, and a MapView placeholder. Full booking UI
is Sprints 1-2; the API in Swagger is the working part in Week 1.

## Option B (Docker, on your own machine)

```bash
docker compose up --build
# API: http://localhost:8000/health
# Web: http://localhost:5173
```
Note: Docker is not installed on the Muse VM used to verify this repo,
so Option A is the verified path here. Docker Compose works on a
normal laptop with Docker Desktop.

## Demo flow to try in Swagger (http://localhost:8000/docs)

On startup the API seeds 24 listings (20 APPROVED, 4 PENDING) and a
demo admin. Demo admin (demo only, change/remove before production):
`admin@staynest.local` / `admin12345`

1. `GET /listings/search?zip=95110&guests=2` — should return listings.
   Try `zip=95110` with no login: search is public.
2. `POST /auth/register` — role HOST, e.g. host@demo.com / password123.
   Then `POST /auth/login` — copy the `access_token`.
3. In Swagger, click Authorize (top right), paste `Bearer <token>`,
   then `POST /listings` — new listing starts `PENDING_APPROVAL`,
   so it will NOT appear in search yet. That is the approval gate working.
4. Log in as the demo admin, then
   `POST /admin/listings/{id}/approve` — now it appears in search.
5. Register a CUSTOMER, log in, then `POST /bookings` for that listing,
   e.g. check_in 2027-05-01, check_out 2027-05-04, guests 2.
   Try the same dates again -> 409. Try 15 days -> 422.
   `GET /bookings/me`, then `POST /bookings/{id}/cancel`.
6. `GET /host/analytics?days=30` and `GET /admin/analytics?days=30`
   (admin token for the second one).

## Troubleshooting

- Search returns `[]`: the listing is probably still PENDING_APPROVAL.
  Approve it as admin first (step 4 above).
- `401` on a protected endpoint: you forgot the Authorize step in
  Swagger, or the token expired (1 hour). Log in again.
- `409` on booking: dates overlap an existing CONFIRMED booking.
  That is the rule working, not a bug.
- Frontend shows seed data but not API data: Week 1 web UI uses a
  seed fallback; API integration for search/book lands in Sprint 1.
  Use Swagger for the live API in Week 1.
- In-memory store: data resets when you restart the API. That is
  intentional for Week 1; PostgreSQL wiring is Sprint 1.

## Domain tests (no server needed)

```bash
python3 backend/tests/test_week1.py -v
# 11 tests: 14-day rule, overlap, guest cap, pending-not-in-search,
# review past/owned/once, cancel, booked-today, analytics scope
```

## Sprints 1-4 — full app (not just Swagger)

After Sprint 1, the web UI is the full app, not a scaffold:
- `/` Search (API, filters, map pins -> detail)
- `/auth` Log in / Register (role nav changes by role)
- `/host` My listings (create/edit/delete, HOST only)
- `/bookings` My bookings (cancel, mark completed, review completed)
- `/admin` Approvals queue (approve/reject/remove, ADMIN only)
- `/analytics` Host/admin dashboards (30/60/90, zip filter)
- `/listings/:id` Detail (photos, amenities, cost, rating, reviews, # booked today, Book form)

Demo in 4 moments, in order: see docs/demo-script.md.
DB mode: `STAYNEST_DB_URL=sqlite:///./staynest.db uvicorn app.main:app --port 8000`
from backend/ — data persists across restarts. Without it, the in-memory
store + seed is used and resets on restart.

## Local run — two terminals, in order, no DB needed (PR 15)

**You do NOT need a database.** Default is in-memory + seed data.
A database is opt-in only (STAYNEST_DB_URL, Sprint 3). If you see a
blank page, it is almost certainly NOT a DB problem — see below.

```bash
# Terminal 1 — backend FIRST (must be running before the frontend)
cd team3-vacation-rentals
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload --port 8000
# Check: curl http://localhost:8000/health  -> {"status":"ok"}

# Terminal 2 — frontend SECOND
cd team3-vacation-rentals/frontend
npm install && npm run dev
# Open: http://localhost:5173
# Check: bash scripts/check_local.sh  (from repo root)
```

**Why the 2026-11-04 console crash happened (fixed in PR 15):**
1. Vite proxy had no rewrite, so `/api/listings/search` was forwarded
   to the backend as `/api/listings/search`, FastAPI returned 404
   `{"detail": "Not Found"}`.
2. The API client only threw when `success === false`. A 404 detail
   body has no `success` field, so it returned `data === undefined`.
3. SearchPage then crashed on `results.length` (line 45 in the screenshot).
Fix: proxy now strips `/api` (dev + preview), the client throws on any
non-OK status or missing data, and SearchPage/MapView guard against
non-array results — a bad API response now shows an error + seed
fallback, never a blank page.

**If you still see the old page:** you are on old code. `git pull
origin main`, stop BOTH servers (Ctrl+C in each terminal), restart
them in order above, then hard-refresh (Ctrl+Shift+R). Vite config
changes need a full dev-server restart, not just a browser refresh.
