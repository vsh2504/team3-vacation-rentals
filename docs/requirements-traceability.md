# Requirements Traceability — Full Product Acceptance

Task 4.2 verification run: **2026-11-04 (America/Los_Angeles)**, re-measured against a live local PostgreSQL 18 cluster, FastAPI, Vite and headless Chrome (Playwright CLI).

Status meanings:

- **Verified** — the named automated check executed successfully in this run.
- **External limitation** — a live third-party or paid provider was intentionally not exercised.

## Measured verification summary

| Verification | Command | Measured result |
|---|---|---|
| Backend suite on PostgreSQL | `STAYNEST_TEST_DB_URL=postgresql+psycopg://staynest@127.0.0.1:55432/staynest_acceptance .venv/bin/python -m pytest tests -q` (from `backend/`) | **66 passed, 0 skipped**, 3 deprecation warnings (62 domain/API tests + 4 PostgreSQL acceptance tests incl. concurrent overlap). |
| Role-based browser acceptance (mocked API) | `cd frontend && npm run test:browser` | **PASS, 10 areas**: unavailable action + geocoding; search + map; booking; 375px mobile layout; host listing management; host analytics; admin approval; admin analytics + ZIP; cancellation; review. |
| Live-stack browser smoke (real API + PostgreSQL) | `STAYNEST_ACCEPTANCE_URL=http://127.0.0.1:5183 npm run test:browser:live` | **PASS, 4 areas**: live search/detail/map; host listings; admin moderation + analytics; mobile layout. |
| Production frontend build | `cd frontend && npm run build` | **Passed**: 56 modules; 630.70 kB JS (145.25 kB gzip); non-failing chunk-size warning. |
| One-command startup | `STAYNEST_API_PORT=8010 STAYNEST_WEB_PORT=5183 ./scripts/start_local.sh` | **Passed**: PostgreSQL, migration, seed (users=5 listings=24), FastAPI and Vite ready; re-run reuses services. |
| Health check | `./scripts/health_local.sh` | **6 passed, 0 failed** (PostgreSQL, schema, API, search, Vite, `/api` proxy). |
| Restart persistence | `stop_local.sh` then `start_local.sh` | Data preserved in `.local/postgres-data`; counts unchanged after restart; health 6/6. |

## Automated coverage map

| Area | Primary automated evidence |
|---|---|
| Search, duration, time, capacity, approval, media, map fields | `backend/tests/test_listings_search.py`; `test_postgres_search_enforces_duration_time_capacity_and_moderation` |
| Registration, login, navigation, RBAC, moderation | `backend/tests/test_auth_admin.py`; `test_postgres_roles_reviews_analytics_and_cancellation` |
| Booking, cancel, overlap, price | `backend/tests/test_bookings.py`; `test_postgres_concurrent_api_requests_create_only_one_confirmed_booking` |
| Reviews and analytics | `backend/tests/test_reviews_analytics.py`; `test_postgres_roles_reviews_analytics_and_cancellation` |
| PostgreSQL persistence and extended listing fields | `test_postgres_restart_reloads_extended_fields_moderation_booking_and_review` |
| Customer/host/admin browser journeys, responsive layout, map interaction | `frontend/tests/staynest-browser-acceptance.js` |
| Browser runner and configuration | `frontend/tests/run-browser-acceptance.sh`; `frontend/.playwright/cli.config.json` |

## Requirement-by-requirement traceability

| Req. | Status | Implementation | Automated evidence / current limitation |
|---|---|---|---|
| 1.1 | Verified in memory; PostgreSQL covered | `SearchQuery`, `ListingService.search/availability`, `/listings/search` | `test_listings_search.py`; PostgreSQL search acceptance covers dates, times, guests, ZIP, approval, and availability. |
| 1.2 | Verified | `SearchQuery`, `BookingIn`, `validate_stay` | Existing backend tests reject zero, negative, and 15-night stays and accept exactly 14 nights; PostgreSQL acceptance repeats the boundary. |
| 1.3 | Verified | listing serializer and `ListingCard` | API tests assert media, amenities, prices, ratings/reviews, capacity, availability, and booked-today; browser flow asserts nightly/total display. |
| 1.4 | Verified | `ListingCard` and `ListingDetailPage` availability actions | Existing API/search tests cover unavailable results; browser fixture exercises the enabled booking path. |
| 1.5 | Verified (API + browser) | OSM URLs/embed fields and `MapView` | API tests cover coordinates/OSM links; browser flow selects a marker and the OpenStreetMap link. Browser flow executed and passed. |
| 1.6 | Verified with provider doubles; external live call limited | `geocoding.py`, `/geocode`, Nominatim default and optional Google provider | `test_listings_search.py` covers provider selection/error mapping without transmitting live addresses. No Google key is configured and live Nominatim was not called. |
| 2.1 | Verified | `/auth/register`, `/auth/login` | `test_auth_admin.py` covers valid customer/host creation, normalization, duplicates, and login. |
| 2.2 | Verified | auth session payload and `App.jsx` role navigation | Backend auth tests assert role navigation; browser flow switches customer, host, and admin sessions. |
| 2.3 | Verified | router/service role and ownership guards | Auth, listing, booking, review, and PostgreSQL acceptance tests assert 401/403/422 boundaries. |
| 2.4 | Verified | seeded admin login, moderation and platform analytics routes | `test_auth_admin.py` and analytics tests; PostgreSQL acceptance logs in through the supported admin flow. |
| 3.1 | Verified | `BookingService.book`, price calculation, `BookingForm` | `test_bookings.py`; browser acceptance submits a reservation and verifies confirmation payload. |
| 3.2 | Verified (in-memory + PostgreSQL race) | in-memory overlap check plus PostgreSQL exclusion constraint | Overlap tests pass; the two-thread PostgreSQL API test executed: exactly one 200, one 409, one confirmed row. |
| 3.3 | Verified | cancel route/service and availability release | `test_bookings.py`; PostgreSQL acceptance verifies cancellation state and analytics exclusion. |
| 3.4 | Verified (API + browser) | booking `stay_state`, tabs, saved OSM location | Booking tests assert state/location; browser review journey renders the completed-stay dashboard. |
| 3.5 | Verified | `ReviewService`, `ReviewForm` | Review tests cover completed past stays and 1–5 validation; browser flow submits a 4-star review. |
| 3.6 | Verified | review ownership/status/uniqueness rules | `test_reviews_analytics.py`; PostgreSQL acceptance repeats other-owner, upcoming, and duplicate rejection. |
| 4.1 | Verified (API + browser) | `ListingIn`, `Listing`, host form | Listing tests cover extended fields; PostgreSQL persistence acceptance reloads contact, hours, coordinates, photos, and video. |
| 4.2 | Verified | create/update reset to `PENDING_APPROVAL`; search requires `APPROVED` | Listing and moderation tests; PostgreSQL search acceptance checks pending exclusion before approval. |
| 4.3 | Verified | `/host/listings` owner scope and moderation status | `test_listings_search.py`; browser host portal asserts pending status. |
| 4.4 | Verified | owner-only update/removal plus SQL flush | Listing tests cover own/other-host behavior; browser flow edits and re-submits a listing. |
| 5.1 | Verified | moderation serializer completeness/host/media evidence | `test_auth_admin.py`; browser queue fixture renders the assessment data. |
| 5.2 | Verified | approve transition controls public search | `test_auth_admin.py`; browser approval flow covered. |
| 5.3 | Verified | reject/remove transitions exclude public search | `test_auth_admin.py`. |
| 5.4 | Verified | admin route guards | Auth tests and PostgreSQL acceptance assert non-admin 403 responses. |
| 6.1 | Verified | `AnalyticsService.host_analytics` | Analytics tests cover 30/60/90, own-listing scope, ZIP totals, and cancellation exclusion. |
| 6.2 | Verified | platform analytics route | Analytics/auth tests cover admin-only platform totals. |
| 6.3 | Verified | filter-before-aggregation behavior | `test_analytics_zip_filter_recomputes_totals`; PostgreSQL acceptance covers empty filtered totals. |
| 6.4 | Verified | cancelled exclusion and exact allowed periods | Analytics tests assert cancelled exclusion and reject 31/45/120-day values. |
| 7.1 | Verified | `scripts/start_local.sh`, PostgreSQL, FastAPI, Vite | Script started PostgreSQL, FastAPI and Vite; health 6/6. |
| 7.2 | Verified | `SqlBackedStore` write-through/flush/reload | PostgreSQL store-reconstruction test passed; script stop/start preserved data. |
| 7.3 | Verified | idempotent migration plus `_seed_empty_database` | Idempotent migration re-applied cleanly; seed ran only on empty DB (users=5 listings=24). |
| 7.4 | Verified | `health_local.sh` | Passing run prints 6/6 with URLs; earlier failure-path run printed URLs, log commands and exit 1. |
| 8.1 | Verified by repository evidence | installed frontend-design skill lock plus `docs/design-system.md` and frontend design tokens | No UI redesign was performed in task 4.2; this task only added acceptance coverage. |
| 8.2 | Verified | responsive CSS, mobile nav, adaptive grids/maps/tables | Browser flow checks a 375×812 viewport, menu expansion, and horizontal overflow. |
| 8.3 | Verified | loading/success/error/empty states across pages | Role journeys assert booking, host edit, admin approval, and review success feedback. Existing code has explicit loading/error/empty states. |
| 8.4 | Verified; contrast manual | labels, landmarks, focus styles, live regions, semantic buttons/tabs/radiogroup | Browser flow uses accessible roles/names for all actions. No automated contrast engine is installed, so contrast remains a manual audit item. |

## External-provider limitations

1. **Google address search:** only selected when a Google key is configured; no key is committed or available in this run.
2. **OpenStreetMap/Nominatim:** API/provider boundaries and OSM URLs are tested with deterministic doubles. Live Nominatim and tile availability are external and were not used as a pass condition.
3. **Azure:** paid live provisioning and a deployed public URL are outside task 4.2 and remain unverified.
4. **Contrast:** no automated contrast engine is installed; WCAG contrast remains a manual audit item.
