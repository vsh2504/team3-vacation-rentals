# Week 1 Scrum Journal — Sprint 0 (Contracts)

**Working days:** Thu 1 Oct, Fri 2 Oct, Sat 3 Oct 2026 (plan).
**Actual repo execution:** 4 Nov 2026 (see README "Week 1" note — commit
timestamps are real, not backdated to October).
**Meeting rhythm:** Face-to-face Thu/Fri/Sat, Google Meet backup, Google Chat
for same-day blockers. Thu = planning, Fri = build + PRs, Sat = review + merge + journal.

## Thu 1 Oct — Day 1: Repo + contracts (planned) / PRs 1-2 (actual)

| Agent | Did / completed | Doing next | Blocked by / on whom |
|---|---|---|---|
| Vinayak Gupta (A) | Repo scaffold, CI, Docker Compose, error envelope, README | JWT + RBAC service, /health | None |
| Ranadheer Reddy Rikala (B) | Listing data model draft, wireframe sketches (search + detail) | Search filter strategies | Blocked: Google Maps API key — awaiting key/quota; workaround: Leaflet + seed coordinates for local dev |
| Manoj (C) | Booking state machine draft, overlap test cases | Availability service with in-memory repo | None |
| Prajval Sudhir (D) | Review + analytics query sketches, admin flow draft | Review service behind COMPLETED check | None |

## Fri 2 Oct — Day 2: Domain + seed + frontend scaffold (planned) / PRs 3-4 (actual)

| Agent | Did / completed | Doing next | Blocked by / on whom |
|---|---|---|---|
| Vinayak Gupta (A) | Auth service (register/login, PBKDF2 + HMAC JWT contract) | Role guards on routers (Sprint 1) | None |
| Ranadheer Reddy Rikala (B) | Listing service (create PENDING, approve gate, search filters) | Listing detail + photos (Sprint 2) | Maps key still pending — mock geocode held |
| Manoj (C) | Availability + booking service, overlap + 14-day + guest tests | My bookings + cancel (Sprint 2) | Blocked (resolved same day): Listing status enum update in B's PR needed a one-line stub update in C's tests |
| Prajval Sudhir (D) | Review service, analytics_by_zip (30/60/90, host scope) | Admin approve/reject UI (Sprint 2) | Blocked: Admin seed account needs Azure DB access (Sprint 3); workaround: local Postgres admin seed |

## Sat 3 Oct — Day 3: Review, merge, journal (planned) / PR 5 + tracker (actual)

| Agent | Did / completed | Doing next | Blocked by / on whom |
|---|---|---|---|
| Vinayak Gupta (A) | Reviewed B/C/D PRs, merged in order, CI green | Sprint 1: auth routers + role guards | None |
| Ranadheer Reddy Rikala (B) | Reviewed A/C PRs, wireframes inventory (18 screens) | Sprint 1: listing CRUD routers | None |
| Manoj (C) | Reviewed A/B PRs, acceptance matrix (Week 1) | Sprint 1: booking create router | None |
| Prajval Sudhir (D) | Reviewed A/B PRs, tracker + journal, analytics tests | Sprint 1: review endpoint router | None |

**Week 1 exit criteria — all met in this repo:**
- [x] `docker compose up` definition runs API + DB + seed (Azure deploy is Sprint 3, not claimed here)
- [x] Domain tests pass (11 tests, stdlib only)
- [x] Contracts frozen in docs/contracts.md + domain.py + services.py
- [x] Seed: 24 listings, 6 cities/zips, 20 APPROVED / 4 PENDING (check seed file)
- [x] Wireframes inventory + tracker + journal in repo
- [ ] UI fully working — explicitly NOT Week 1 (sheet status: UI not started; Week 1 is scaffold + wireframes only)
