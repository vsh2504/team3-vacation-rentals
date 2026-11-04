# Full acceptance run — Sprints 1-4 (run 2026-11-04, localhost)

Run: domain tests + API smoke + load test + frontend build + CI.
Results below are measured, not planned.

| Requirement | Test | Result |
|---|---|---|
| Max stay 14 days | Book/search 15 days | 422, domain test + API smoke (PR 9, re-verified PR 11-14) |
| Overlap blocked | Book overlapping CONFIRMED dates | 409, domain test + load test (5 workers: 1 success, 4 conflicts) |
| Guest cap | Book 5 guests in max 4 home | 422, domain test |
| Pending not in search | PENDING listing in seed | Excluded, API: pending count 4, search 95110 = 4 approved |
| Review past only | Review CONFIRMED / completed / twice | Blocked / allowed / 409, domain + service test |
| Cancel owned CONFIRMED only | Cancel other user's / completed | Blocked, domain test |
| Analytics 30/60/90 + host scope | Host A vs B, cancelled excluded | Tested; rentals = distinct listings (Sprint 3 fix) |
| Role enforcement | Customer POST /listings, non-admin approve | 403, API smoke |
| Admin queue | GET /admin/listings?status=PENDING_APPROVAL | 4 pending seed listings returned |
| Photos in API | GET /listings/1 | photos array returned (seed Unsplash URL) |
| DB persistence | STAYNEST_DB_URL=sqlite, create, restart, reload | Row persisted across restarts (verified) |
| Frontend build | npm run build | Pass, 44 modules, 198 kB JS |
| CI | PR + main runs | Green on PR 9, PR 10; PR 11-14 to be verified on merge |
| Azure live URL | Deployed URL acceptance (US27) | NOT DONE — blocked on Vin approval for paid Azure provisioning. Localhost + Bicep templates are the Sprint 3 evidence, not a live URL. |

Full product acceptance on a deployed URL (US27) is the one story
that cannot be closed without the Azure approval above. Everything
else in US01-US32 is implemented in code and verified on localhost.
