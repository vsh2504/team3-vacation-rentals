# Acceptance — Week 1 (run against domain tests + contract, not a finished UI)

| Requirement | Test | Result (Week 1) |
|---|---|---|
| Max stay 14 days | Book/search 15 days | 422 path in domain.validate_stay, tested (exactly 14 allowed) |
| Overlap blocked | Book overlapping CONFIRMED dates | 409 path in BookingService, tested; checkout day is free |
| Guest cap | Book 5 guests in max_guests=4 home | 422, tested |
| Pending not in search | PENDING listing in seed | Excluded from search_listings, tested |
| Review past only | Review CONFIRMED booking | Blocked, tested; one review per booking, tested |
| Cancel owned CONFIRMED only | Cancel other user's / completed booking | Blocked, tested |
| Analytics 30/60/90 + host scope | Host A vs Host B, cancelled excluded | Tested; days other than 30/60/90 rejected |
| Role enforcement | Customer POST /listings, non-admin approve | FORBIDDEN in services, tested via service guards |
| Error envelope | Every ApiError | envelope() shape, see core/errors.py |

Run: `python3 -m unittest backend/tests/test_week1.py -v`
Full product acceptance (deployed URL) is Sprint 3 — Week 1 does not claim it.
