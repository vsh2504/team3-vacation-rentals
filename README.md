# StayNest — Team 3 Vacation Rental Booking Platform

An Airbnb-style end-to-end platform to search, book, manage, and review
vacation rentals, with separate Customer, Host, and Admin experiences,
on one JSON API.

**Company / product:** StayNest (Team 3)
**Tech stack:** Python FastAPI, React.js, PostgreSQL, Azure
**Working days:** Thursday, Friday, Saturday — every week.
Thu = planning + contracts, Fri = build + PRs, Sat = review + merge + journal.
**Meeting rhythm:** Face-to-face Thu/Fri/Sat, Google Meet as backup,
Google Chat for same-day blockers.

## Team — AI agents / workstreams (feature ownership from Sprint 1)

See `docs/feature-breakdown.md` for the full breakdown — every feature
has API + UI + DB + tests + its own DevOps piece + its own deployment
proof + a Demo Day moment. No one is only DevOps, only UI, or only docs.

| Feature | Agent | API + UI | DevOps + deployment |
|---|---|---|---|
| Find a Stay (Search, Maps, Detail) | Vinayak Gupta (team lead) | Search, map, detail | Frontend deploy, CDN, Maps key, search health check |
| Identity, Platform & Admin Control | Ranadhir Reddy Rikkala | Auth, RBAC, admin moderation | LB, VM Scale Set, CI baseline, Key Vault, main deploy/rollback |
| Book & Cancel a Stay | Manoj | Availability, book, cancel | Postgres migrations, backup, load test, DB deploy |
| Trust, Reviews & Analytics | Prajval Sudhir | Reviews, host/admin dashboards | Monitoring, analytics job, alerts, health dashboard |

Week 1 note: Week 1 PRs used Slice A-D labels for contract scaffolding
(A Vinayak platform, B Ranadheer listings, C Manoj booking, D Prajval
reviews/analytics). That history is kept as-is; feature ownership above
governs Sprint 1 onward. Name spelling: team file says Ranadhir Reddy
Rikkala; Week 1 repo used Ranadheer Reddy Rikala — confirm before grading.

## Week 1 — what is in this repo (Thu 1 Oct – Sat 3 Oct 2026 scope)

Week 1 is Sprint 0: contracts before code. It does **not** claim a finished
booking UI. It delivers, in five incremental PRs:

1. `a/repo-scaffold` — repo, CI, Docker, contracts, README
2. `b/domain-models` — domain classes, repositories, services (frozen contracts)
3. `c/seed-frontend-wireframes` — seed data, React scaffold, wireframes
4. `d/tests-acceptance` — pure-Python tests, acceptance matrix, journal
5. `e/tracker-docs` — Jira-like tracker (CSV in repo, Excel attached to the Week 1 report), proposal summary

Each PR is small, reviewed in its description by another slice, and merged
in order. Commit timestamps on GitHub are the real push dates (Nov 2026
execution of the Oct Week 1 scope) — they are not backdated to October.
The Week 1 journal in `docs/journal/week1-scrum.md` separates
*planned* Week 1 dates (Thu 1 – Sat 3 Oct) from *actual* repo dates.

## Quick start (local)

```bash
docker compose up --build
# API: http://localhost:8000/health
# API docs (FastAPI): http://localhost:8000/docs
# Frontend: http://localhost:5173
```

Without Docker, the Week 1 domain tests run with only the Python standard
library (no FastAPI install needed for the domain layer):

```bash
python3 backend/tests/test_week1.py -v
# or: python3 backend/tests/test_week1.py
```

## API contract (summary — full contract in docs/contracts.md)

- All input/output JSON. One error envelope everywhere (see docs/contracts.md).
- Auth: `POST /auth/register` (CUSTOMER or HOST only; Admin is seeded),
  `POST /auth/login` returns JWT with `sub`, `role`, `exp`.
- Search: `GET /listings/search?check_in&check_out&guests&city&state&zip`
- Listings: `POST /listings` (Host), `PUT /listings/{id}` (own only),
  `DELETE /listings/{id}` (own only), `GET /host/listings`.
- Bookings: `POST /bookings`, `GET /bookings/me`, `POST /bookings/{id}/cancel`.
- Reviews: `POST /reviews` (COMPLETED bookings only, one per booking).
- Admin: `POST /admin/listings/{id}/approve|reject`, `DELETE /admin/listings/{id}`,
  `GET /admin/analytics?days=30|60|90&zip=`.
- Host analytics: `GET /host/analytics?days=30|60|90&zip=`.

Hard rules, enforced in the service layer and tested in Week 1:
- Max stay 14 days: `checkout - checkin <= 14`, else 422.
- No overlapping CONFIRMED booking for the same listing, else 409.
- `guests <= listing.max_guests`, else 422.
- Only APPROVED listings appear in search.
- Reviews only on COMPLETED bookings owned by the reviewer, else 422/403.

## Authorship — read before judging contributions

This repo was created under the GitHub account `vsh2504` (Vinayak Gupta).
All pushes through the Muse GitHub connector are therefore authored by
that account in GitHub's records. Slice ownership in CODEOWNERS, PR
descriptions, file headers, the tracker, and the journal shows which
agent workstream each change belongs to — but it does **not** claim that
the other three agents pushed from their own GitHub accounts, because
they did not, and their credentials were not available to this session.
If the course requires four distinct GitHub authors, each teammate must
push their own slice from their own account; this repo's branch/PR
structure is designed so that handover is a clean per-slice transfer.

## Links (fill in after the team repo is shared)

- Project Journal: `docs/journal/` in this repo (Week 1: `docs/journal/week1-scrum.md`)
- Tracker: `tracking/` in this repo (CSV) + Excel workbook delivered with the Week 1 report
- Full proposal: `docs/Team3_Vacation_Rentals_Proposal.md` (v2)
- Deployed URL: TBD in Sprint 3 (Azure VM Scale Set + Load Balancer) — not claimed in Week 1

## Sprints 1-4 — what is implemented (all weeks, 2026-11-04)

Week 1 was contracts. Sprints 1-4 are the full product, in PRs per sprint:

- **Sprint 1:** Auth UI, search via API, listing detail, My Bookings,
  review form, admin queue endpoint, booking complete endpoint.
- **Sprint 2:** Map (OSM embed / Google Maps embed with key, pins =
  results, click pin -> detail), host listing CRUD UI, admin moderation
  UI, search filters (city/state/zip/guests/dates), photos in API.
- **Sprint 3:** Analytics dashboards (host/admin, 30/60/90, zip),
  analytics rentals = distinct listings, SQL persistence
  (STAYNEST_DB_URL, SQLite verified, Postgres via docker-compose),
  migration 001_init.sql, backup script, parallel load test
  (5 workers: 1 success, 4 conflicts — no double-booking),
  Azure Bicep template (VMSS + LB + Postgres + Blob + Key Vault +
  App Insights) — templates only, NOT provisioned.
- **Sprint 4:** Demo script (4 moments), full acceptance run
  (docs/acceptance-full.md), journals per sprint, tracker updated.

Run it: see RUNNING.md (API + web, Swagger demo flow, demo admin).

## What is NOT done — honestly
- **Live Azure URL (US27):** not provisioned. It needs Vin's explicit
  approval for a specific paid Azure deployment. The Bicep template,
  migration, and CI deploy-check are the Sprint 3 evidence; localhost
  + docker-compose are the verified deployment equivalent.
- **Live Google Maps API key:** not committed (correctly). OSM embed
  works without a key; Google Maps embed works with VITE_GOOGLE_MAPS_KEY.
- **Real Blob photo upload:** host photo URLs are accepted in the
  listing form; Blob upload wiring is a Sprint 3 template item, not a
  live endpoint, for the same no-cloud-account reason as above.

## Frontend split — everyone gets a named frontend piece (PR 12)

Same idea as the backend core APIs, for the web UI. See
docs/frontend-breakdown.md for the full table; summary:

- **Vinayak Gupta:** Search, Listing detail, Host listings, Listing card, Map
- **Ranadhir Reddy Rikkala:** Auth page, Admin page, App shell / role nav / routing
- **Manoj:** My bookings page, Booking form component
- **Prajval Sudhir:** Analytics page, Review form component
- **Shared (no single owner):** api/client.js — the only place the frontend touches HTTP

Cross-feature use is explicit: BookingForm (Manoj) is rendered inside
ListingDetail (Vinayak), ReviewForm (Prajval) inside Bookings (Manoj) —
ownership follows the file, not the screen it appears on.
