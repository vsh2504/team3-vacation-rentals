# API & Data Contracts — Frozen Week 1 (Sprint 0)

Frozen by: Thu–Sat Week 1 working days (Thu 1, Fri 2, Sat 3 Oct 2026 plan).
Change rule: a contract change needs a migration PR + updated OpenAPI +
updated tests in the same PR. Never a silent edit in one slice.

## 1. Endpoints (full list in README)

Auth: POST /auth/register (CUSTOMER|HOST), POST /auth/login, GET /auth/me.
Listings/Search: GET /listings/search, GET /listings/{id}, POST /listings,
PUT /listings/{id}, DELETE /listings/{id}, GET /host/listings.
Bookings: POST /bookings, GET /bookings/me, POST /bookings/{id}/cancel.
Reviews: POST /reviews, GET /listings/{id}/reviews.
Admin: POST /admin/listings/{id}/approve, POST /admin/listings/{id}/reject,
DELETE /admin/listings/{id}, GET /admin/analytics?days=30|60|90&zip=.
Host analytics: GET /host/analytics?days=30|60|90&zip=. Health: GET /health.

## 2. Data model v1

users(id, email unique, password_hash, full_name, role CUSTOMER|HOST|ADMIN, phone, created_at)
listings(id, host_id->users, title, description, address, city, state, zip, lat, lng,
  price_per_night, max_guests, bedrooms, bathrooms, amenities JSON array,
  available_times, status PENDING_APPROVAL|APPROVED|REJECTED|REMOVED)
listing_photos(id, listing_id, blob_url, media_type photo|video, sort_order)
bookings(id, listing_id, customer_id, check_in, check_out, guests, total_price,
  status CONFIRMED|CANCELLED|COMPLETED, booked_date, cancelled_at)
reviews(id, booking_id unique, listing_id, customer_id, rating 1-5, comment, created_at)

## 3. Error envelope (every endpoint)

Success: {"success": true, "data": {...}, "error": null}
Error: {"success": false, "data": null,
  "error": {"code": "VALIDATION_ERROR", "message": "Stay cannot exceed 14 days", "field": "check_out"}}
Codes: VALIDATION_ERROR 422, UNAUTHORIZED 401, FORBIDDEN 403, NOT_FOUND 404,
CONFLICT 409 (e.g. overlapping booking), SERVER_ERROR 500.

## 4. Validation rules

Search/booking: check_in >= today (Sprint 1, with a testable clock),
check_out > check_in, (check_out - check_in).days <= 14, guests >= 1,
guests <= listing.max_guests, no overlapping CONFIRMED booking
(overlap = check_in < existing.check_out AND check_out > existing.check_in).
Review: rating 1-5, booking COMPLETED, reviewer owns booking, one review per booking.
Analytics: days must be exactly 30, 60, or 90; cancelled bookings excluded;
host scope = caller's listings only; admin scope = all.

## 5. Availability, pricing, '# booked today'

Available iff status == APPROVED AND dates inside available_times AND no
overlapping CONFIRMED booking. total_price = price_per_night * nights.
'# booked today' = count of bookings for that listing with
booked_date == today (America/Los_Angeles), regardless of stay dates.

## 6. Design patterns

Repository (services -> repository Protocol, never raw SQL in routers),
Service + DTO, Dependency Injection (FastAPI Depends), Strategy (search
filters composed in SearchService), State Machine (bookings
CONFIRMED -> COMPLETED|CANCELLED), Observer (lightweight in-process
BookingCreated/Cancelled events for analytics + '# booked today'),
Role Guard (@require_role / @require_owner, API-enforced, UI is only a hint).
