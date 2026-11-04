# Feature Breakdown — Everyone Gets API + DevOps + Deployment

## Why this replaces the old "one person does all DevOps" split

Week 1 used Slice A-D labels for contract scaffolding:
A Vinayak = platform, B Ranadheer = listings/search, C Manoj = booking,
D Prajval = reviews/analytics. That left DevOps concentrated in Slice A.

From Sprint 1 onward, work is divided **by feature, not by layer**.
Every feature bundle below has, by design:
API + UI + DB + tests + its own DevOps piece + its own deployment
(step, health check, rollback) + a Demo Day moment.
No one is "only docs", "only UI", or "only DevOps".

## Ownership note — Vinayak / Ranadhir swap

The team file recorded on 2026-11-04 lists a different split from the
Week 1 repo: Vinayak (team lead) = Listings, Search & Maps;
Ranadhir = Identity, RBAC, platform, Azure deployment.
Week 1 PR history cannot be rewritten honestly, so it stays as-is:
Week 1 was contract scaffolding, not feature delivery.
From Sprint 1, feature ownership follows the team file below.
If the team wants the Week 1 labels to match instead, that is a
documentation rename only — it does not change any code or PR history.

## Feature 1 — Find a Stay (Search, Maps, Listing Detail)
**Owner: Vinayak Gupta (team lead) — largest bundle, demo opener**

- API: GET /listings/search (date, guests, duration, availability,
  city/state/zip), GET /listings/{id}, address search / geocode
- UI: Search, Results list, Map view, Listing detail
  (photos/videos, amenities, cost, rating, reviews, # booked today, Book button)
- DB: listings, listing_photos
- Hard problem: filter composition (Strategy pattern) + 14-day rule +
  availability join, without duplicating booking logic
- Tests: search filters, zip/guest, pending-not-in-search, map pin = result
- DevOps (this feature's own): Frontend deploy — React build, CDN/static
  hosting, Google Maps API key management + quota alert, frontend CI job,
  search health check (`GET /listings/search` smoke test)
- Deployment proof: deploy frontend to demo env, search returns seed
  listings, rollback = previous frontend build
- Demo moment (1): Search San Jose, 4 guests, 3 nights -> map + list -> open a listing
- Stories: US10, US11, US12, US13, US29 (see tracking/backlog.csv)

## Feature 2 — Identity, Platform & Admin Control
**Owner: Ranadhir Reddy Rikkala (spelling as in team file; repo Week 1
used "Ranadheer Reddy Rikala" — confirm spelling before grading)**

- API: POST /auth/register, POST /auth/login, GET /auth/me,
  POST /admin/listings/{id}/approve|reject, DELETE /admin/listings/{id}
- UI: Register, Login, Role-based home/nav, Admin approvals queue, Moderation
- DB: users
- Hard problem: stateless JWT behind a load balancer (no sticky sessions),
  server-side RBAC on every endpoint, secret management (no secrets in Git)
- Tests: register/login, duplicate email, wrong password, role 403 cases,
  approve -> appears in search / reject -> does not
- DevOps (this feature's own): Platform baseline — Azure Load Balancer,
  VM Scale Set (min 2, CPU > 70% scale-out), GitHub Actions CI baseline,
  Azure Key Vault, main deploy + rollback script, `/health` monitoring
- Deployment proof: deploy API to VMSS, LB serves both instances,
  rollback = previous VM image / previous deploy
- Demo moment (3): Log in as Admin, approve a pending listing, it appears
  in search; log in as each role and show nav + API change by role
- Stories: US01, US02, US03, US21, US22, US30

## Feature 3 — Book & Cancel a Stay
**Owner: Manoj (Manoj Ganjigatte Manjunatha in team file)**

- API: POST /bookings, GET /bookings/me, POST /bookings/{id}/cancel,
  availability check (service-level)
- UI: Booking form + confirmation, My bookings, Cancel confirmation
- DB: bookings
- Hard problem: overlapping-booking race (DB transaction + overlap check),
  14-day + guest-cap validation, pricing (nights x price_per_night),
  cancel -> dates become available again
- Tests: overlap blocked (checkout day free), 15-day rejected, guest cap,
  cancel owned CONFIRMED only, cancel -> rebook succeeds, parallel-booking race
- DevOps (this feature's own): Database deploy — PostgreSQL migrations,
  backup/restore check, connection pooling, DB deploy script,
  booking load test (parallel attempts, no double-booking)
- Deployment proof: deploy migration to demo DB, booking smoke test passes,
  rollback = previous migration + data check
- Demo moment (2): Book a stay, try the same dates again (blocked),
  cancel it, dates free again
- Stories: US14, US15, US16, US17, US31

## Feature 4 — Trust, Reviews & Analytics
**Owner: Prajval Sudhir**

- API: POST /reviews, GET /listings/{id}/reviews,
  GET /host/analytics?days=30|60|90&zip=, GET /admin/analytics?days=30|60|90&zip=
- UI: Review form (past bookings only), Host analytics dashboard,
  Platform analytics dashboard
- DB: reviews
- Hard problem: aggregation by zip + 30/60/90-day window, host-scope
  isolation (Host A never sees Host B), one review per booking,
  COMPLETED-only eligibility
- Tests: review past/owned/once, rating 1-5, analytics totals,
  cancelled excluded, host scope, days other than 30/60/90 rejected
- DevOps (this feature's own): Observability — Application Insights /
  Log Analytics, analytics scheduled job, alerts (error rate, LB health),
  demo-env health dashboard, analytics smoke test
- Deployment proof: deploy analytics job + dashboards to demo env,
  dashboards match bookings in period, rollback = previous dashboard build
- Demo moment (4): Submit a review on a past booking -> rating updates;
  Host sees bookings by zip, 30/60/90; Admin sees platform totals
- Stories: US18, US19, US20, US23, US32

## Shared DevOps rotation — everyone deploys, no one only watches

Each feature owner deploys their own feature (above) in Sprint 3.
In addition, one person per sprint is Deploy Captain (Thu/Fri/Sat):
they run the shared deploy, watch CI + LB health, and write the deploy
note in the journal. Rotation, so everyone has done the shared deploy:

| Sprint | Deploy Captain | Shared deploy focus |
|---|---|---|
| Sprint 1 (13-26 Oct scope) | Ranadhir | CI baseline + Docker + demo env skeleton |
| Sprint 2 (27 Oct-9 Nov scope) | Vinayak | Frontend deploy + Maps key + CDN |
| Sprint 3 (10-23 Nov scope) | Manoj | DB migration + load test + Azure demo env live |
| Sprint 4 / Demo (24-30 Nov) | Prajval | Monitoring + demo env reset + rollback rehearsal |

## Balance check — type, not just points

| Agent | API | UI | DB | Tests | DevOps (own) | Deployment proof | Demo moment |
|---|---|---|---|---|---|---|---|
| Vinayak — Find a Stay | Yes | Yes | listings | Yes | Frontend/CDN/Maps | Yes | Search + map opener |
| Ranadhir — Identity/Platform/Admin | Yes | Yes | users | Yes | LB/VMSS/CI/Key Vault | Yes | 3-role login + approve |
| Manoj — Book & Cancel | Yes | Yes | bookings | Yes | Postgres/migrations/load test | Yes | Book/block/cancel |
| Prajval — Reviews/Analytics | Yes | Yes | reviews | Yes | Monitoring/analytics job | Yes | Review + dashboards |

Points (backlog US01-US32): Find a Stay ~35 + 5 DevOps = 40,
Identity/Platform/Admin ~26 + 5 = 31, Book & Cancel ~21 + 5 = 26,
Reviews/Analytics ~29 + 5 = 34, plus shared stories.
Search is still the largest feature — that is why the team lead owns it —
but every agent now has the same *kinds* of work, and every agent has a
deployment they can point to on Demo Day.

## Definition of Done for a feature (all four, no exceptions)

Code + API tests + UI happy path + own DevOps piece deployed +
health check passing + rollback tested + journal row + PR reviewed by
another feature owner. A feature without its deployment proof is not Done,
even if its API works on localhost.
