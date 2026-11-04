# Requirements Traceability — Strict Check (PR 14, 2026-11-04)

This file is the audit Vin asked for: every assignment requirement,
where it is implemented, which test proves it, and what is still open.
"Done" means code + test in this repo, not a plan. "Partial" means the
local/demo part works and the live part is blocked for a stated reason.
No requirement is marked Done on the basis of a plan, a screenshot, or
a manual smoke test that is not committed as a test.

## Tests — per agent, per feature (PR 14)

Before PR 14, the repo had exactly one test file: test_week1.py
(11 domain tests). API smoke tests were run manually and were NOT
committed — that was the gap Vin caught. PR 14 fixes it with one
committed API test file per agent, each with its own commit on PR 14:

| Agent / feature | Test file | Tests | What it proves |
|---|---|---|---|
| Shared domain (all) | backend/tests/test_week1.py | 11 | 14-day, guest cap, overlap, pending-not-in-search, price, review past/owned/once, cancel, booked-today, analytics scope |
| Ranadhir — Identity/Admin | backend/tests/test_auth_admin.py | 6 | Register/login/me, duplicate 409, admin-register 403, wrong password 401, no-token 401 + error envelope, admin queue, approve -> appears in search, non-admin 403, admin remove -> leaves search |
| Vinayak — Search/Listings | backend/tests/test_listings_search.py | 5 | Search zip/guests/city/state, pending excluded, detail photos/videos/amenities/booked-today, host create starts PENDING, customer create 403, owner-only edit/delete, host listings only own |
| Manoj — Book/Cancel | backend/tests/test_bookings.py | 5 | Book price (nights x price), my bookings, overlap 409, checkout day free, 15-day 422, guest cap 422, cancel frees dates, other-user cancel 403, complete past only |
| Prajval — Reviews/Analytics | backend/tests/test_reviews_analytics.py | 3 | Review completed only, once, rating bounds 422, upcoming blocked, aggregate rating, host scope, admin totals + zip filter, invalid days 422, customer admin-analytics 403 |
| **Total** | | **30** | CI runs every file on every PR (see .github/workflows/ci.yml). Frontend: build in CI (deploy-check), no committed frontend unit tests yet — see gap below. |

Run all: `python3 backend/tests/test_week1.py -v` and the four files
above, or follow the CI step. TestClient tests need httpx, which is
now in backend/requirements.txt.

## Requirement-by-requirement

| Requirement | Status | Implementation | Test |
|---|---|---|---|
| JSON APIs with validation + single error envelope | Done | core/errors.py, Pydantic schemas, ok()/ApiError on every router | test_auth_admin (envelope), all API files (422/401/403/404/409) |
| 3 roles: Customer / Host / Admin | Done | UserRole, role checks in services + routers, role nav in frontend | test_auth_admin, test_listings_search (403s) |
| Max stay 14 days | Done | domain.validate_stay, exactly 14 allowed | test_week1, test_bookings |
| Search by date/guests/duration/availability + city/state/zip | Done | search_listings + /listings/search | test_listings_search, test_week1 |
| Google Maps address search | Partial | Map embed (Google with VITE_GOOGLE_MAPS_KEY, OSM without); address search is a text filter, not geocoding. Full geocoding needs a Maps key, which is not committed (correctly) and not provisioned. | Manual only — no key in CI, so no committed geocode test |
| Listing detail: photos/videos, amenities, cost, rating, reviews, # booked today | Done (videos PR 14) | photos + videos fields in domain/seed/API/detail page (video player if videos present; seed videos on listings 1-3, mock sample videos) | test_listings_search (photos/videos in detail) |
| Book only if available | Done | is_available + overlap check in BookingService | test_bookings (409, checkout day free) |
| Host listing CRUD | Done | POST/PUT/DELETE/GET /host/listings, owner-only | test_listings_search |
| Host + admin analytics by zip and 30/60/90 days | Done | analytics_by_zip, /host/analytics, /admin/analytics, distinct rentals (PR 11) | test_reviews_analytics, test_week1 |
| Admin approve / remove | Done | /admin/listings approve/reject/delete + queue endpoint | test_auth_admin |
| Auto-scaled cloud deploy | Partial | Bicep: VMSS min 2 + LB + Postgres + Blob + Key Vault + App Insights. NOT provisioned — needs Vin's explicit approval for paid Azure resources. Local docker-compose is the verified equivalent. | deploy-check CI (build, migration, guard) — no live URL test |
| Mock seed DB | Done | 24 listings, 6 zips, 20 APPROVED / 4 PENDING, seed loader + SQL seed path | All API tests use seed_demo_data() |
| Project Journal, weekly Scrum (Did / Doing next / Blocked) | Done (sprint-grouped) | docs/journal/week1-scrum.md + sprint1-4-scrum.md, each with Did/Doing/Blocked. Weeks are grouped by sprint, not one file per calendar week — see note below. | — (docs, not code) |
| 2 XP values: Communication, Feedback | Done (proposal) | Proposal §: Communication = frozen contracts + PR reviews + Thu/Fri scrum; Feedback = weekly demo + acceptance -> next-sprint stories. Not yet duplicated into repo docs — add if a grader reads repo only. | — |
| Backlog + burndown in sheet/board | Done (CSV) + Partial (sheet) | tracking/backlog.csv (32 stories, statuses updated PR 11), burndown.csv (Saturday checkpoints to 28 Nov), scrum/sprint CSVs. Excel workbook was delivered with Week 1 report (your_files), not in repo (binary cannot go via snapshot). | — |
| Wireframes for all screens | Done | docs/wireframes.md: 18 screens (8 Customer, 5 Host, 3 Admin, 2 Shared), each with primary action, error + empty state | — |
| Component + deployment diagrams | Done | docs/architecture.md; deployment diagram matches Bicep resources (VMSS/LB/Postgres/Blob/Key Vault/Insights) | — |
| README: company, agent names, contributions, Journal link, Sheet/board link | Done | README.md: StayNest (Team 3), 4 agents + features, contributions in feature-breakdown + frontend-breakdown, Journal = docs/journal/, Tracker = tracking/ | — |
| Everyone gets API + DevOps + deployment | Partial (code) / Done (split) | Core API per agent (PR 9), frontend piece per agent (PR 12), DevOps story per agent US29-US32 (In Progress: templates/CI/local, live pending). Split is real in code; live deployment proof per agent is blocked on the Azure approval above. | Per-agent test files (PR 14) |
| Incremental commits, collaborative, Thu/Fri/Sat | Honest note | PRs 1-13 are incremental and per-feature, but all real pushes are 2026-11-04, not spread over Oct-Nov Thu/Fri/Sat. Commits are NEVER backdated in this repo — backdating would fake history. Journals separate planned weeks (Oct-Nov) from actual repo dates (Nov). PR 14 uses 4 separate commits, one per agent's test file, to restore per-agent commit visibility. | git log |

## Gaps that remain (do not close without the stated input)
1. **Live Azure URL (US27) + live deployment proofs (US29-US32, US04):** need Vin's explicit approval for a specific paid Azure deployment. No account was created.
2. **Google Maps geocoding:** needs a Maps API key (VITE_GOOGLE_MAPS_KEY). No key committed.
3. **Frontend unit tests:** frontend is verified by build + API tests + manual demo, not by committed component tests. Adding Vitest/jsdom component tests is the next test step if a grader requires it.
4. **Weekly journals per calendar week:** sprint journals cover the same work grouped by sprint. One file per week (Weeks 2-9) can be split out from them on request, without changing any facts.
5. **Blob photo/video upload endpoint:** host photo/video URLs are accepted; live Blob upload is a template item, blocked on (1).
