# Scrum Journal — Sprint 1 (Weeks 2-3 scope, implemented 2026-11-04)

Working days Thu/Fri/Sat, per team plan. Dates below are the plan scope
from docs/feature-breakdown.md, not backdated history: Week 1 was
2026-11-04 in real repo time; Sprints 1-4 were implemented in sequence
on 2026-11-04 at Vin's "implement everything, for each week" direction,
with one PR per sprint so CI stays green between sprints.

## Did
- Vinayak — Search UI now calls the API (not seed fallback); detail page
  with photos, amenities, cost, rating, reviews, # booked today, Book form.
- Ranadhir — Auth pages (register/login, role nav, token in localStorage);
  admin approvals queue endpoint GET /admin/listings?status=.
- Manoj — My Bookings page, cancel, complete (past stays -> COMPLETED).
- Prajval — Review form on completed bookings; listing reviews in detail.

## Doing next
- Sprint 2: map pins, host CRUD UI, admin moderation UI, analytics UI.

## Blocked
- None in Sprint 1. Google Maps key/quota (BLK-1) still open — OSM embed
  is the fallback, Google Maps embed is used only if VITE_GOOGLE_MAPS_KEY is set.
